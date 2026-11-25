"""
Step 2: Spatial Metrics from GHSL for Year 2014 (T2)

Open-source Python 3 implementation of the original ArcPy script.
Extracts spatial metrics from the Global Human Settlement Layer (GHSL)
for the year 2014 using IndiFrag methodology.

Reference: Sapena et al. (2020) https://doi.org/10.3390/ijgi9070436
Data source GHSL: https://doi.org/10.2905/jrc-ghsl-10007

Note: This script requires Step 1 to be run first (uses FUA boundaries created in Step 1).
"""

import argparse
import sys
import time

import geopandas as gpd
import numpy as np
from shapely.ops import unary_union

from utils import BOUNDARIES_PATH as BOUNDARIES_DIR

# Import local utilities
from utils import (
    OUTPUT_PATH,
    calc_compactness,
    calc_dispersion_index,
    calc_elongation_ratio,
    count_raster_pixels,
    create_fishnet_points,
    ensure_dir,
    get_mbr_dimensions,
    get_raster_value_counts,
    get_utm_epsg,
    identify_second_urban_core,
    identify_urban_core,
    polygonize_raster,
    reclassify_raster,
    standard_distance,
)

# =============================================================================
# Configuration
# =============================================================================

DATE = 2014

# Input paths
BOUNDARIES_PATH = BOUNDARIES_DIR / "Boundaries_3857.shp"

# Use clipped rasters from Step 1
RAS_3857_DIR = OUTPUT_PATH / "Ras_3857"
FUA_DIR = OUTPUT_PATH / "FUAs"

# Output directories (created in main() before processing)
VEC_14_DIR = OUTPUT_PATH / "Vec_14"
RAS_14_DIR = OUTPUT_PATH / "Ras_14"

# Output shapefile with results
OUTPUT_SHP = OUTPUT_PATH / "Boundaries_SM_2014.shp"

# GHSL reclassification for year 2014
# Original values: 0=nodata, 1-2=not built, 3=built 1975-1990, 4=built 1990-2000, 5=built 2000-2014, 6=built 2014+
# For 2014: values 3, 4, 5, 6 are built-up
RECLASS_2014 = {
    0: None,  # NoData
    1: None,  # Not built
    2: None,  # Not built
    3: 1,     # Built 1975-1990 -> built
    4: 1,     # Built 1990-2000 -> built
    5: 1,     # Built 2000-2014 -> built
    6: 1,     # Built 2014+ -> built
}

# Cloud cover threshold (percentage)
CLOUD_THRESHOLD = 1.0


# =============================================================================
# Main Processing Functions
# =============================================================================

def initialize_output_shapefile():
    """
    Create output shapefile with metric fields.

    Returns
    -------
    GeoDataFrame
        Copy of boundaries with added metric fields
    """
    print("Initializing output shapefile...")
    gdf = gpd.read_file(BOUNDARIES_PATH)

    # Add metric fields for T2
    metric_fields = [
        'AreaFUA',    # Area of FUA in km²
        'UA_T2',      # Urban Area
        'C_T2',       # Compactness
        'DI_T2',      # Dispersion Index
        'AWSD_T2',    # Area-Weighted Standard Distance
        'DU_T2',      # Urban Density (%)
        'L_UC_T2',    # Largest Urban Core (%)
        'C_UC_T2',    # Urban Core Compactness
        'SL_UC_T2',   # Second Largest Urban Core (%)
        'ER_UC_T2',   # Elongation Ratio
        'Clouds',     # Cloud cover percentage
    ]

    for field in metric_fields:
        gdf[field] = np.nan

    return gdf


def process_fua(fua_code, fua_geometry):
    """
    Process a single FUA and calculate spatial metrics for 2014.

    Parameters
    ----------
    fua_code : str
        FUA code identifier
    fua_geometry : shapely geometry
        FUA boundary geometry (in EPSG:3857)

    Returns
    -------
    dict
        Dictionary of calculated metrics
    """
    metrics = {
        'fuacode_si': fua_code,
        'Clouds': 0.0
    }

    try:
        # =================================================================
        # Step 1: Check for clipped raster from Step 1
        # =================================================================
        input_ras = RAS_3857_DIR / f"BUILT_{fua_code}_3857.tif"

        if not input_ras.exists():
            print(f"  WARNING: Clipped raster not found: {input_ras}")
            print("  Run Step 1 first to create clipped rasters.")
            return metrics

        # =================================================================
        # Step 2: Get UTM zone via direct calculation
        # =================================================================
        print("  Finding UTM projection...")

        # Convert centroid to WGS84 for UTM calculation
        from pyproj import Transformer
        centroid = fua_geometry.centroid
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(centroid.x, centroid.y)
        epsg = get_utm_epsg(lon, lat)

        # Create and project FUA boundary to UTM
        fua_gdf = gpd.GeoDataFrame(
            {'fuacode_si': [fua_code]},
            geometry=[fua_geometry],
            crs="EPSG:3857"
        )
        fua_utm = fua_gdf.to_crs(f"EPSG:{epsg}")

        print(f"  Using EPSG:{epsg}")

        # Area of FUA in km²
        area_fua = fua_utm.geometry.area.sum() / 1_000_000
        metrics['AreaFUA'] = area_fua

        # =================================================================
        # Step 3: Check cloud cover (use same check as Step 1)
        # =================================================================
        print("  Checking cloud cover...")
        value_counts = get_raster_value_counts(input_ras)
        n_null = value_counts.get(0, 0)
        n_total = sum(value_counts.values())

        if n_total > 0:
            cloud = (n_null * 100) / n_total
        else:
            cloud = 0

        metrics['Clouds'] = cloud

        if cloud >= CLOUD_THRESHOLD:
            print(f"  WARNING: Cloud cover {cloud:.1f}% exceeds threshold. Skipping...")
            return metrics

        # =================================================================
        # Step 4: Reclassify to built-up for year 2014
        # =================================================================
        print("  Reclassifying raster for year 2014...")
        output_ras = RAS_14_DIR / f"BUILT_{fua_code}_{DATE}_3857.tif"

        reclassify_raster(
            input_ras,
            RECLASS_2014,
            output_ras,
            nodata_value=0
        )

        # Count built-up pixels
        n_pixels = count_raster_pixels(output_ras, value=1)
        if n_pixels == 0:
            print("  WARNING: No built-up pixels found. Skipping...")
            return metrics

        # =================================================================
        # Step 5: Polygonize raster and project to UTM
        # =================================================================
        print("  Polygonizing raster...")
        # Polygonize to memory (no intermediate file write)
        built_gdf = polygonize_raster(output_ras, crs="EPSG:3857")

        print("  Projecting to UTM...")
        built_utm = built_gdf.to_crs(f"EPSG:{epsg}")

        # Calculate area and perimeter
        built_utm['Area'] = built_utm.geometry.area
        built_utm['Perim'] = built_utm.geometry.length

        output_vec_utm = VEC_14_DIR / f"BUILT_{fua_code}_{DATE}_{epsg}.shp"
        built_utm.to_file(output_vec_utm)

        # =================================================================
        # Step 7: Calculate spatial metrics for built-up area
        # =================================================================
        print("  Calculating built-up area metrics...")

        # Total urban area and perimeter
        area_u = built_utm['Area'].sum()
        perim_u = built_utm['Perim'].sum()
        n_patches = len(built_utm)

        # Urban Area (UA) in km²
        metrics['UA_T2'] = area_u / 1_000_000

        # Urban Density (DU) in %
        metrics['DU_T2'] = (area_u / 1_000_000) / area_fua * 100

        # Compactness (C)
        metrics['C_T2'] = calc_compactness(area_u, perim_u)

        # Dispersion Index (DI)
        largest_area = built_utm['Area'].max()
        metrics['DI_T2'] = calc_dispersion_index(n_patches, n_pixels, largest_area, area_u)

        # Area-Weighted Standard Distance (AWSD)
        print("  Calculating AWSD...")
        sd_weighted = standard_distance(built_utm, weight_col='Area')

        # Normalization: create fishnet and calculate max SD
        bounds = fua_utm.total_bounds
        cell_size = 2000  # 2km grid
        fishnet = create_fishnet_points(bounds, cell_size, fua_utm.union_all())
        if len(fishnet) > 0:
            fishnet = fishnet.set_crs(f"EPSG:{epsg}")
            sd_max = standard_distance(fishnet)
            if sd_max > 0:
                metrics['AWSD_T2'] = (sd_weighted * 100) / sd_max
            else:
                metrics['AWSD_T2'] = 0
        else:
            metrics['AWSD_T2'] = 0

        # =================================================================
        # Step 8: Calculate urban core metrics
        # =================================================================
        print("  Identifying urban core (UMZ)...")

        # First urban core
        core1 = identify_urban_core(built_utm, area_col='Area', distance=200, iterations=3)

        if len(core1) > 0:
            # Mark UMZ in built_utm
            built_utm['UMZ'] = 0
            built_utm.loc[core1.index, 'UMZ'] = 1

            # Area of urban core
            a_umz = core1['Area'].sum()

            # Largest Urban Core (L_UC)
            metrics['L_UC_T2'] = (a_umz / area_u) * 100

            # Urban Core Compactness (C_UC)
            perim_umz = core1['Perim'].sum()
            metrics['C_UC_T2'] = calc_compactness(a_umz, perim_umz)

            # Elongation Ratio (ER_UC)
            core_union = unary_union(core1.geometry)
            width, length = get_mbr_dimensions(core_union)
            metrics['ER_UC_T2'] = calc_elongation_ratio(a_umz, length)

            # Second Urban Core (SL_UC)
            # SL_UC is the largest single connected component of the secondary core
            print("  Identifying second urban core...")
            core2 = identify_second_urban_core(built_utm, core1, area_col='Area', distance=200, iterations=3)

            if len(core2) > 0:
                built_utm.loc[core2.index, 'UMZ'] = 2
                # Find largest connected component within core2
                core2_union = unary_union(core2.geometry)
                if core2_union.geom_type == 'MultiPolygon':
                    largest_component = max(core2_union.geoms, key=lambda g: g.area)
                    a_umz2 = largest_component.area
                else:
                    a_umz2 = core2_union.area
                metrics['SL_UC_T2'] = (a_umz2 / area_u) * 100
            else:
                metrics['SL_UC_T2'] = 0

            # Save updated shapefile with UMZ field
            built_utm.to_file(output_vec_utm)

        print("  Metrics calculated successfully.")

    except Exception as e:
        print(f"  ERROR processing FUA {fua_code}: {e}")
        import traceback
        traceback.print_exc()

    return metrics


def main():
    """Main processing function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Calculate spatial metrics from GHSL for year 2014 (T2).'
    )
    parser.add_argument(
        '--country', '-c',
        type=str,
        default=None,
        help='Filter FUAs by country code prefix (e.g., US, AUS, EUR). '
             'Can specify multiple comma-separated codes (e.g., US,CA).'
    )
    parser.add_argument(
        '--fua', '-f',
        type=str,
        default=None,
        help='Process specific FUA code(s), comma-separated (e.g., USA01,USA02).'
    )
    args = parser.parse_args()

    start_time = time.time()
    print("=" * 60)
    print("Step 2: Spatial Metrics from GHSL for Year 2014")
    print("=" * 60)

    # Check for Step 1 outputs
    if not RAS_3857_DIR.exists() or len(list(RAS_3857_DIR.glob("*.tif"))) == 0:
        print(f"\nERROR: Step 1 outputs not found at:\n{RAS_3857_DIR}")
        print("\nPlease run Step 1 first.")
        sys.exit(1)

    # Ensure output directories exist before writing
    for d in (OUTPUT_PATH, VEC_14_DIR, RAS_14_DIR):
        ensure_dir(d)

    # Initialize output
    results_gdf = initialize_output_shapefile()

    # Get list of FUAs with optional filtering
    fua_codes = results_gdf['fuacode_si'].tolist()

    if args.fua:
        # Filter to specific FUA codes
        specified_fuas = [f.strip() for f in args.fua.split(',')]
        fua_codes = [f for f in fua_codes if f in specified_fuas]
        print(f"\nFiltering to {len(fua_codes)} specified FUA(s)...")

    elif args.country:
        # Filter by country prefix
        country_prefixes = tuple(c.strip().upper() for c in args.country.split(','))
        fua_codes = [f for f in fua_codes if f.upper().startswith(country_prefixes)]
        print(f"\nFiltering to country code(s): {', '.join(country_prefixes)}")

    n_fuas = len(fua_codes)
    print(f"Processing {n_fuas} FUAs...")

    # Process each FUA
    for i, fua_code in enumerate(fua_codes):
        fua_start = time.time()
        print(f"\n[{i+1}/{n_fuas}] Processing FUA: {fua_code}")

        # Get FUA geometry
        fua_row = results_gdf[results_gdf['fuacode_si'] == fua_code].iloc[0]
        fua_geometry = fua_row.geometry

        # Process FUA
        metrics = process_fua(fua_code, fua_geometry)

        # Update results
        idx = results_gdf[results_gdf['fuacode_si'] == fua_code].index[0]
        for key, value in metrics.items():
            if key in results_gdf.columns:
                results_gdf.loc[idx, key] = value

        elapsed = time.time() - fua_start
        print(f"  Time: {elapsed/60:.2f} min")

    # Filter to only processed FUAs (those with data)
    processed_gdf = results_gdf[results_gdf['fuacode_si'].isin(fua_codes)].copy()

    # Save results as shapefile
    print(f"\nSaving results to {OUTPUT_SHP}...")
    processed_gdf.to_file(OUTPUT_SHP)

    # Save results as CSV (without geometry, easier for analysis)
    OUTPUT_CSV = OUTPUT_PATH / "Boundaries_SM_2014.csv"
    csv_cols = ['fuacode_si', 'AreaFUA', 'UA_T2', 'C_T2', 'DI_T2', 'AWSD_T2',
                'DU_T2', 'L_UC_T2', 'C_UC_T2', 'SL_UC_T2', 'ER_UC_T2', 'Clouds']
    processed_gdf[csv_cols].to_csv(OUTPUT_CSV, index=False)
    print(f"Saving CSV to {OUTPUT_CSV}...")

    # Print summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("Processing complete!")
    print(f"Total time: {total_time/60:.2f} minutes")
    print(f"Output: {OUTPUT_SHP}")
    print(f"Output: {OUTPUT_CSV}")
    print("=" * 60)


if __name__ == "__main__":
    main()
