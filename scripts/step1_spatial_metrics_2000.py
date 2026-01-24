# -*- coding: utf-8 -*-
"""
Step 1: Spatial Metrics from GHSL for Year 2000 (T1)

Open-source Python 3 implementation of the original ArcPy script.
Extracts spatial metrics from the Global Human Settlement Layer (GHSL)
for the year 2000 using IndiFrag methodology.

Reference: Sapena et al. (2020) https://doi.org/10.3390/ijgi9070436
Data source GHSL: https://doi.org/10.2905/jrc-ghsl-10007

Required: GHSL raster data must be extracted to DATA/GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0/
"""

import os
import sys
import time
import argparse
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.ops import unary_union

# Import local utilities
from utils import (
    PROJECT_ROOT, DATA_PATH, OUTPUT_PATH,
    BOUNDARIES_PATH as BOUNDARIES_DIR,
    UTM_ZONES_PATH as UTM_ZONES_DIR,
    GHSL_PATH as GHSL_DIR,
    standard_distance, create_fishnet_points, get_mbr_dimensions,
    calc_compactness, calc_dispersion_index, calc_elongation_ratio,
    identify_urban_core, identify_second_urban_core,
    clip_raster_to_geometry, reclassify_raster, polygonize_raster,
    count_raster_pixels, get_raster_value_counts,
    lookup_utm_from_shapefile, reproject_geodataframe,
    ensure_dir, get_fua_list
)

# =============================================================================
# Configuration
# =============================================================================

DATE = 2000

# Input paths
BOUNDARIES_PATH = BOUNDARIES_DIR / "Boundaries_3857.shp"
UTM_ZONES_PATH = UTM_ZONES_DIR / "UTM_Zone_EPSG_3857.shp"
GHSL_VRT = GHSL_DIR / "V2-0" / "GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0.vrt"

# Output directories
VEC_3857_DIR = ensure_dir(OUTPUT_PATH / "Vec_3857")
RAS_3857_DIR = ensure_dir(OUTPUT_PATH / "Ras_3857")
FUA_DIR = ensure_dir(OUTPUT_PATH / "FUAs")
VEC_00_DIR = ensure_dir(OUTPUT_PATH / "Vec_00")
RAS_00_DIR = ensure_dir(OUTPUT_PATH / "Ras_00")

# Output shapefile with results
OUTPUT_SHP = OUTPUT_PATH / "Boundaries_SM_2000.shp"

# GHSL reclassification for year 2000
# Original values: 0=nodata, 1-3=not built, 4=built 1975-1990, 5=built 1990-2000, 6=built 2000-2014
# For 2000: values 4, 5, 6 are built-up (built by 2000 or later in multitemporal)
RECLASS_2000 = {
    0: None,  # NoData
    1: None,  # Not built
    2: None,  # Not built
    3: None,  # Not built
    4: 1,     # Built by 1990 -> built
    5: 1,     # Built 1990-2000 -> built
    6: 1,     # Built 2000-2014 -> built (exists in 2000)
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

    # Add metric fields
    metric_fields = [
        'AreaFUA',    # Area of FUA in km²
        'UA_T1',      # Urban Area
        'C_T1',       # Compactness
        'DI_T1',      # Dispersion Index
        'AWSD_T1',    # Area-Weighted Standard Distance
        'DU_T1',      # Urban Density (%)
        'L_UC_T1',    # Largest Urban Core (%)
        'C_UC_T1',    # Urban Core Compactness
        'SL_UC_T1',   # Second Largest Urban Core (%)
        'ER_UC_T1',   # Elongation Ratio
        'Clouds',     # Cloud cover percentage
    ]

    for field in metric_fields:
        gdf[field] = np.nan

    return gdf


def process_fua(fua_code, fua_geometry, utm_zones_gdf, results_gdf):
    """
    Process a single FUA and calculate spatial metrics.

    Parameters
    ----------
    fua_code : str
        FUA code identifier
    fua_geometry : shapely geometry
        FUA boundary geometry (in EPSG:3857)
    utm_zones_gdf : GeoDataFrame
        UTM zones for EPSG lookup
    results_gdf : GeoDataFrame
        Results GeoDataFrame to update

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
        # Step 1: Clip GHSL raster to FUA boundary
        # =================================================================
        print(f"  Clipping GHSL raster...")
        output_ras_all = RAS_3857_DIR / f"BUILT_{fua_code}_3857.tif"

        clip_raster_to_geometry(
            GHSL_VRT,
            fua_geometry,
            output_ras_all,
            nodata=7
        )

        # =================================================================
        # Step 2: Get UTM zone and project FUA boundary
        # =================================================================
        print(f"  Determining UTM zone...")
        centroid = fua_geometry.centroid

        # Find UTM zone
        epsg = None
        for idx, row in utm_zones_gdf.iterrows():
            if row.geometry.contains(centroid):
                epsg = int(row['EPSG'])
                break

        if epsg is None:
            # Fallback: calculate from coordinates
            # Transform centroid to WGS84 first
            from pyproj import Transformer
            transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(centroid.x, centroid.y)
            zone = int((lon + 180) / 6) + 1
            epsg = 32600 + zone if lat >= 0 else 32700 + zone

        print(f"  Using EPSG:{epsg}")

        # Create FUA GeoDataFrame and project to UTM
        fua_gdf = gpd.GeoDataFrame(
            {'fuacode_si': [fua_code]},
            geometry=[fua_geometry],
            crs="EPSG:3857"
        )
        fua_utm = fua_gdf.to_crs(f"EPSG:{epsg}")
        fua_utm.to_file(FUA_DIR / f"FUA_{fua_code}_{epsg}.shp")

        # Area of FUA in km²
        area_fua = fua_utm.geometry.area.sum() / 1_000_000
        metrics['AreaFUA'] = area_fua

        # =================================================================
        # Step 3: Check cloud cover
        # =================================================================
        print(f"  Checking cloud cover...")
        value_counts = get_raster_value_counts(output_ras_all)
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
        # Step 4: Reclassify to built-up for year 2000
        # =================================================================
        print(f"  Reclassifying raster for year 2000...")
        output_ras = RAS_00_DIR / f"BUILT_{fua_code}_{DATE}_3857.tif"

        reclassify_raster(
            output_ras_all,
            RECLASS_2000,
            output_ras,
            nodata_value=0
        )

        # Count built-up pixels
        n_pixels = count_raster_pixels(output_ras, value=1)
        if n_pixels == 0:
            print(f"  WARNING: No built-up pixels found. Skipping...")
            return metrics

        # =================================================================
        # Step 5: Polygonize raster
        # =================================================================
        print(f"  Polygonizing raster...")
        output_vec_3857 = VEC_3857_DIR / f"BUILT_{fua_code}_{DATE}_3857.shp"

        built_gdf = polygonize_raster(
            output_ras,
            output_vec_3857,
            crs="EPSG:3857"
        )

        # =================================================================
        # Step 6: Project to UTM
        # =================================================================
        print(f"  Projecting to UTM...")
        built_utm = built_gdf.to_crs(f"EPSG:{epsg}")

        # Calculate area and perimeter
        built_utm['Area'] = built_utm.geometry.area
        built_utm['Perim'] = built_utm.geometry.length

        output_vec_utm = VEC_00_DIR / f"BUILT_{fua_code}_{DATE}_{epsg}.shp"
        built_utm.to_file(output_vec_utm)

        # =================================================================
        # Step 7: Calculate spatial metrics for built-up area
        # =================================================================
        print(f"  Calculating built-up area metrics...")

        # Total urban area and perimeter
        area_u = built_utm['Area'].sum()
        perim_u = built_utm['Perim'].sum()
        n_patches = len(built_utm)

        # Urban Area (UA) in km²
        metrics['UA_T1'] = area_u / 1_000_000

        # Urban Density (DU) in %
        metrics['DU_T1'] = (area_u / 1_000_000) / area_fua * 100

        # Compactness (C)
        metrics['C_T1'] = calc_compactness(area_u, perim_u)

        # Dispersion Index (DI)
        largest_area = built_utm['Area'].max()
        metrics['DI_T1'] = calc_dispersion_index(n_patches, n_pixels, largest_area, area_u)

        # Area-Weighted Standard Distance (AWSD)
        print(f"  Calculating AWSD...")
        sd_weighted = standard_distance(built_utm, weight_col='Area')

        # Normalization: create fishnet and calculate max SD
        bounds = fua_utm.total_bounds
        cell_size = 2000  # 2km grid
        fishnet = create_fishnet_points(bounds, cell_size, fua_utm.unary_union)
        if len(fishnet) > 0:
            fishnet = fishnet.set_crs(f"EPSG:{epsg}")
            sd_max = standard_distance(fishnet)
            if sd_max > 0:
                metrics['AWSD_T1'] = (sd_weighted * 100) / sd_max
            else:
                metrics['AWSD_T1'] = 0
        else:
            metrics['AWSD_T1'] = 0

        # =================================================================
        # Step 8: Calculate urban core metrics
        # =================================================================
        print(f"  Identifying urban core (UMZ)...")

        # First urban core
        core1 = identify_urban_core(built_utm, area_col='Area', distance=200, iterations=3)

        if len(core1) > 0:
            # Mark UMZ in built_utm
            built_utm['UMZ'] = 0
            built_utm.loc[core1.index, 'UMZ'] = 1

            # Area of urban core
            a_umz = core1['Area'].sum()

            # Largest Urban Core (L_UC)
            metrics['L_UC_T1'] = (a_umz / area_u) * 100

            # Urban Core Compactness (C_UC)
            perim_umz = core1['Perim'].sum()
            metrics['C_UC_T1'] = calc_compactness(a_umz, perim_umz)

            # Elongation Ratio (ER_UC)
            core_union = unary_union(core1.geometry)
            width, length = get_mbr_dimensions(core_union)
            metrics['ER_UC_T1'] = calc_elongation_ratio(a_umz, length)

            # Second Urban Core (SL_UC)
            # SL_UC is the largest single connected component of the secondary core
            print(f"  Identifying second urban core...")
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
                metrics['SL_UC_T1'] = (a_umz2 / area_u) * 100
            else:
                metrics['SL_UC_T1'] = 0

            # Save updated shapefile with UMZ field
            built_utm.to_file(output_vec_utm)

        print(f"  Metrics calculated successfully.")

    except Exception as e:
        print(f"  ERROR processing FUA {fua_code}: {e}")
        import traceback
        traceback.print_exc()

    return metrics


def main():
    """Main processing function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Calculate spatial metrics from GHSL for year 2000 (T1).'
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
    print("Step 1: Spatial Metrics from GHSL for Year 2000")
    print("=" * 60)

    # Check for GHSL data
    if not Path(GHSL_VRT).exists():
        print(f"\nERROR: GHSL data not found at:\n{GHSL_VRT}")
        print("\nPlease download and extract GHSL data to:")
        print(f"  {GHSL_DIR}")
        sys.exit(1)

    # Initialize output
    results_gdf = initialize_output_shapefile()

    # Load UTM zones
    print("\nLoading UTM zones...")
    utm_zones = gpd.read_file(UTM_ZONES_PATH)

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
        metrics = process_fua(fua_code, fua_geometry, utm_zones, results_gdf)

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
    OUTPUT_CSV = OUTPUT_PATH / "Boundaries_SM_2000.csv"
    csv_cols = ['fuacode_si', 'AreaFUA', 'UA_T1', 'C_T1', 'DI_T1', 'AWSD_T1',
                'DU_T1', 'L_UC_T1', 'C_UC_T1', 'SL_UC_T1', 'ER_UC_T1', 'Clouds']
    processed_gdf[csv_cols].to_csv(OUTPUT_CSV, index=False)
    print(f"Saving CSV to {OUTPUT_CSV}...")

    # Print summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"Processing complete!")
    print(f"Total time: {total_time/60:.2f} minutes")
    print(f"Output: {OUTPUT_SHP}")
    print(f"Output: {OUTPUT_CSV}")
    print("=" * 60)


if __name__ == "__main__":
    main()
