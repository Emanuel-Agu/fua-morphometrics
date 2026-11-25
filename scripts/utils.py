"""
Utility functions for spatio-temporal analysis of urban growth.

This module provides open-source replacements for ArcPy functions used in the
original Sapena et al. (2020) analysis pipeline.

Reference: https://doi.org/10.3390/ijgi9070436
"""

import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.mask import mask
from shapely import minimum_rotated_rectangle, unary_union
from shapely.geometry import Point, shape

# =============================================================================
# Configuration
# =============================================================================

# Project root (repository root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data paths
DATA_PATH = PROJECT_ROOT / "data"
BOUNDARIES_PATH = DATA_PATH / "boundaries"
UTM_ZONES_PATH = DATA_PATH / "utm_zones"
PREPROCESSED_PATH = DATA_PATH / "preprocessed"

# External data (large files not in git)
DATA_EXTERNAL_PATH = PROJECT_ROOT / "data_external"
GHSL_PATH = DATA_EXTERNAL_PATH / "GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0"

# Output paths
OUTPUT_PATH = PROJECT_ROOT / "outputs"

# Legacy alias for backward compatibility
BASE_PATH = PROJECT_ROOT


# =============================================================================
# Spatial Statistics Functions
# =============================================================================

def standard_distance(gdf, weight_col=None):
    """
    Calculate standard distance (spatial dispersion measure).

    Equivalent to arcpy.StandardDistance_stats()

    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame with polygon geometries
    weight_col : str, optional
        Column name for area weighting

    Returns
    -------
    float
        Standard distance in CRS units
    """
    if len(gdf) == 0:
        return 0.0

    centroids = np.array([[g.centroid.x, g.centroid.y] for g in gdf.geometry])

    if weight_col and weight_col in gdf.columns:
        weights = gdf[weight_col].values.astype(float)
        if weights.sum() == 0:
            return 0.0
        weights = weights / weights.sum()
        mean_center = np.average(centroids, axis=0, weights=weights)
        variance = np.average((centroids - mean_center)**2, axis=0, weights=weights)
    else:
        mean_center = centroids.mean(axis=0)
        variance = ((centroids - mean_center)**2).mean(axis=0)

    return np.sqrt(variance.sum())


def create_fishnet_points(bounds, cell_size, clip_geometry=None):
    """
    Create a fishnet grid of points.

    Equivalent to arcpy.CreateFishnet_management() with LABELS option.

    Parameters
    ----------
    bounds : tuple
        (minx, miny, maxx, maxy)
    cell_size : float
        Grid cell size in CRS units
    clip_geometry : shapely geometry, optional
        Geometry to clip points to

    Returns
    -------
    GeoDataFrame
        GeoDataFrame with grid points
    """
    minx, miny, maxx, maxy = bounds
    x_coords = np.arange(minx + cell_size/2, maxx, cell_size)
    y_coords = np.arange(miny + cell_size/2, maxy, cell_size)

    points = []
    for x in x_coords:
        for y in y_coords:
            pt = Point(x, y)
            if clip_geometry is None or clip_geometry.contains(pt):
                points.append(pt)

    return gpd.GeoDataFrame(geometry=points, crs=None)


def get_mbr_dimensions(geometry):
    """
    Get width and length of minimum bounding rectangle.

    Equivalent to arcpy.MinimumBoundingGeometry_management() with MBG_FIELDS.

    Parameters
    ----------
    geometry : shapely geometry
        Input geometry (can be polygon or multipolygon)

    Returns
    -------
    tuple
        (width, length) where length >= width
    """
    if geometry.is_empty:
        return 0.0, 0.0

    mbr = minimum_rotated_rectangle(geometry)

    if mbr.is_empty or mbr.geom_type == 'Point':
        return 0.0, 0.0

    coords = list(mbr.exterior.coords)

    edge1 = Point(coords[0]).distance(Point(coords[1]))
    edge2 = Point(coords[1]).distance(Point(coords[2]))

    width = min(edge1, edge2)
    length = max(edge1, edge2)

    return width, length


# =============================================================================
# Metric Calculation Functions
# =============================================================================

def calc_compactness(area, perimeter):
    """
    Calculate compactness index (isoperimetric ratio).

    C = (2 * sqrt(pi * A)) / P * 100

    Parameters
    ----------
    area : float
        Total area
    perimeter : float
        Total perimeter

    Returns
    -------
    float
        Compactness index (0-100, where 100 is a perfect circle)
    """
    if perimeter == 0:
        return 0.0
    return (2 * math.sqrt(math.pi * area)) / perimeter * 100


def calc_dispersion_index(n_patches, n_pixels, largest_patch_area, total_area):
    """
    Calculate dispersion index.

    DI = (((n-1)/(pixels-1)) * 100 + (100 - LPI)) / 2

    Parameters
    ----------
    n_patches : int
        Number of patches
    n_pixels : int
        Number of pixels
    largest_patch_area : float
        Area of largest patch
    total_area : float
        Total urban area

    Returns
    -------
    float
        Dispersion index
    """
    if n_pixels <= 1 or total_area == 0:
        return 0.0

    lpi = (largest_patch_area / total_area) * 100
    di = ((((n_patches - 1) / (n_pixels - 1)) * 100) + (100 - lpi)) / 2
    return di


def calc_elongation_ratio(area, mbr_length):
    """
    Calculate elongation ratio.

    ER = (2 * sqrt(A / pi)) / L

    Parameters
    ----------
    area : float
        Area of the urban core
    mbr_length : float
        Length of minimum bounding rectangle

    Returns
    -------
    float
        Elongation ratio (0-1, where 1 is circular)
    """
    if mbr_length == 0:
        return 0.0
    diameter = 2 * math.sqrt(area / math.pi)
    return diameter / mbr_length


# =============================================================================
# Urban Morphological Zone (UMZ) Functions
# =============================================================================

def identify_urban_core(gdf, area_col='Area', distance=200, iterations=3):
    """
    Identify the Urban Morphological Zone (largest urban core).

    UMZ is defined as "a set of urban areas lying less than 200m apart".
    Starting from the largest patch, iteratively select patches within
    the specified distance.

    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame with urban patches
    area_col : str
        Column containing area values
    distance : float
        Buffer distance in meters (default 200)
    iterations : int
        Number of selection iterations (default 3)

    Returns
    -------
    GeoDataFrame
        Subset of gdf belonging to the urban core
    """
    if len(gdf) == 0:
        return gdf.iloc[0:0]  # Empty GeoDataFrame

    # Find largest patch
    largest_idx = gdf[area_col].idxmax()

    # Initialize with largest patch
    core_indices = {largest_idx}

    # Iteratively expand selection
    for _ in range(iterations):
        # Get current core geometry
        core_geom = unary_union(gdf.loc[list(core_indices)].geometry)
        core_buffer = core_geom.buffer(distance)

        # Find patches within buffer
        for idx, row in gdf.iterrows():
            if idx not in core_indices:
                if row.geometry.intersects(core_buffer):
                    core_indices.add(idx)

    return gdf.loc[list(core_indices)].copy()


def identify_second_urban_core(gdf, first_core_gdf, area_col='Area', distance=200, iterations=3):
    """
    Identify the second largest urban core.

    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame with all urban patches
    first_core_gdf : GeoDataFrame
        GeoDataFrame with first urban core patches
    area_col : str
        Column containing area values
    distance : float
        Buffer distance in meters
    iterations : int
        Number of selection iterations

    Returns
    -------
    GeoDataFrame
        Subset of gdf belonging to the second urban core
    """
    # Exclude first core patches
    remaining = gdf.loc[~gdf.index.isin(first_core_gdf.index)].copy()

    if len(remaining) == 0:
        return gdf.iloc[0:0]  # Empty GeoDataFrame

    return identify_urban_core(remaining, area_col, distance, iterations)


# =============================================================================
# Raster Processing Functions
# =============================================================================

def clip_raster_to_geometry(raster_path, geometry, output_path, nodata=None):
    """
    Clip a raster to a geometry boundary.

    Equivalent to gdalwarp with -cutline option.

    Parameters
    ----------
    raster_path : str or Path
        Input raster path
    geometry : shapely geometry
        Clipping geometry
    output_path : str or Path
        Output raster path
    nodata : number, optional
        NoData value for output

    Returns
    -------
    str
        Path to output raster
    """
    with rasterio.open(raster_path) as src:
        # Mask the raster
        out_image, out_transform = mask(src, [geometry], crop=True, nodata=nodata)
        out_meta = src.meta.copy()

        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata": nodata if nodata is not None else src.nodata
        })

        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)

    return str(output_path)


def reclassify_raster(raster_path, reclass_dict, output_path, nodata_value=None):
    """
    Reclassify raster values.

    Equivalent to arcpy.gp.Reclassify_sa().

    Parameters
    ----------
    raster_path : str or Path
        Input raster path
    reclass_dict : dict
        Dictionary mapping old values (or ranges) to new values.
        Can use tuples for ranges: {(0, 3): nodata, (4, 6): 1}
    output_path : str or Path
        Output raster path
    nodata_value : number, optional
        Value to treat as nodata in output

    Returns
    -------
    str
        Path to output raster
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        out_data = np.zeros_like(data)

        for key, new_val in reclass_dict.items():
            if isinstance(key, tuple):
                # Range: (min, max)
                mask = (data >= key[0]) & (data <= key[1])
            else:
                # Single value
                mask = (data == key)

            if new_val is None or (nodata_value is not None and new_val == nodata_value):
                out_data[mask] = nodata_value if nodata_value is not None else 0
            else:
                out_data[mask] = new_val

        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "nodata": nodata_value
        })

        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_data, 1)

    return str(output_path)


def polygonize_raster(raster_path, output_path=None, crs=None):
    """
    Convert raster to vector polygons.

    Equivalent to gdal_polygonize.py.

    Parameters
    ----------
    raster_path : str or Path
        Input raster path
    output_path : str or Path, optional
        Output shapefile path (if None, returns GeoDataFrame only)
    crs : CRS, optional
        Output CRS (uses raster CRS if not specified)

    Returns
    -------
    GeoDataFrame
        Polygonized raster
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        raster_crs = src.crs if crs is None else crs

        # Generate shapes
        results = []
        for geom, value in shapes(data, transform=transform):
            if value != src.nodata and value != 0:
                results.append({
                    'geometry': shape(geom),
                    'DN': int(value)
                })

    gdf = gpd.GeoDataFrame(results, crs=raster_crs)

    if output_path:
        gdf.to_file(output_path)

    return gdf


def count_raster_pixels(raster_path, value=None):
    """
    Count pixels in a raster, optionally filtered by value.

    Parameters
    ----------
    raster_path : str or Path
        Input raster path
    value : number, optional
        If provided, count only pixels with this value

    Returns
    -------
    int
        Pixel count
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        if value is not None:
            return int(np.sum(data == value))
        else:
            nodata = src.nodata
            if nodata is not None:
                return int(np.sum(data != nodata))
            return int(data.size)


def get_raster_value_counts(raster_path):
    """
    Get counts of each unique value in a raster.

    Equivalent to building a raster attribute table.

    Parameters
    ----------
    raster_path : str or Path
        Input raster path

    Returns
    -------
    dict
        Dictionary mapping values to counts
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        values, counts = np.unique(data, return_counts=True)
        return dict(zip(values.astype(int), counts.astype(int), strict=True))


# =============================================================================
# Coordinate System Functions
# =============================================================================

def get_utm_epsg(longitude, latitude):
    """
    Get the appropriate UTM EPSG code for a given coordinate.

    Parameters
    ----------
    longitude : float
        Longitude in degrees
    latitude : float
        Latitude in degrees

    Returns
    -------
    int
        EPSG code for the appropriate UTM zone
    """
    zone = int((longitude + 180) / 6) + 1

    if latitude >= 0:
        # Northern hemisphere
        epsg = 32600 + zone
    else:
        # Southern hemisphere
        epsg = 32700 + zone

    return epsg


def lookup_utm_from_shapefile(point_geometry, utm_zones_path):
    """
    Look up UTM zone from a UTM zones shapefile.

    This replicates the original workflow that uses a UTM zones shapefile
    with EPSG codes stored in an 'EPSG' field.

    Parameters
    ----------
    point_geometry : shapely Point
        Point to look up
    utm_zones_path : str or Path
        Path to UTM zones shapefile

    Returns
    -------
    int
        EPSG code
    """
    utm_zones = gpd.read_file(utm_zones_path)

    # Find intersecting zone
    for _idx, row in utm_zones.iterrows():
        if row.geometry.contains(point_geometry):
            return int(row['EPSG'])

    # Fallback: calculate UTM zone from coordinates
    return get_utm_epsg(point_geometry.x, point_geometry.y)


def reproject_geodataframe(gdf, target_crs):
    """
    Reproject a GeoDataFrame to a target CRS.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input GeoDataFrame
    target_crs : CRS or int
        Target CRS (can be EPSG code)

    Returns
    -------
    GeoDataFrame
        Reprojected GeoDataFrame
    """
    return gdf.to_crs(target_crs)


# =============================================================================
# File I/O Helpers
# =============================================================================

def ensure_dir(path):
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def get_fua_list(boundaries_path):
    """
    Get list of FUA codes from boundaries shapefile.

    Parameters
    ----------
    boundaries_path : str or Path
        Path to FUA boundaries shapefile

    Returns
    -------
    list
        List of FUA codes
    """
    gdf = gpd.read_file(boundaries_path)
    return gdf['fuacode_si'].tolist()


# =============================================================================
# Growth Classification Functions (for step 5)
# =============================================================================

def calc_landscape_expansion_index(patch_geometry, all_patches_geometry):
    """
    Calculate Landscape Expansion Index (LEI) for a new urban patch.

    LEI = shared_boundary / perimeter

    Parameters
    ----------
    patch_geometry : shapely geometry
        The new patch geometry
    all_patches_geometry : shapely geometry
        Union of all existing urban patches

    Returns
    -------
    float
        LEI value (0 = Outlying, 0-0.5 = Edge-Expansive, >0.5 = Infilling)
    """
    perimeter = patch_geometry.length
    if perimeter == 0:
        return 0.0

    # Calculate shared boundary
    boundary = patch_geometry.boundary
    intersection = boundary.intersection(all_patches_geometry.boundary)
    shared_length = intersection.length if not intersection.is_empty else 0

    lei = shared_length / perimeter
    return lei


def classify_growth_type(lei):
    """
    Classify urban growth type based on LEI.

    Parameters
    ----------
    lei : float
        Landscape Expansion Index

    Returns
    -------
    str
        Growth type: 'Outlying', 'Edge-Expansive', or 'Infilling'
    """
    if lei < 0.0001:
        return 'Outlying'
    elif lei <= 0.5:
        return 'Edge-Expansive'
    else:
        return 'Infilling'
