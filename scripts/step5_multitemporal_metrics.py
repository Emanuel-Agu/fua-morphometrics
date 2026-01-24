# -*- coding: utf-8 -*-
"""
Step 5: Multi-Temporal Metrics (2000-2014)

Open-source Python 3 implementation of the original ArcPy script.
Computes change metrics by comparing T1 (2000) and T2 (2014) built-up areas.

Metrics calculated:
- UCR: Urban Change Rate
- AWMEI: Area-Weighted Mean Expansion Index
- AWMAI: Area-Weighted Mean Accessibility Index

Reference: Sapena et al. (2020) https://doi.org/10.3390/ijgi9070436

Required: Steps 1, 2, and 3 must be run first.
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
    calc_landscape_expansion_index, classify_growth_type,
    ensure_dir
)

# =============================================================================
# Configuration
# =============================================================================

# Input paths
BOUNDARIES_PATH = BOUNDARIES_DIR / "Boundaries_3857.shp"

# Outputs from previous steps
VEC_00_DIR = OUTPUT_PATH / "Vec_00"
VEC_14_DIR = OUTPUT_PATH / "Vec_14"
ROADS_PJ_DIR = OUTPUT_PATH / "ROADs_PJ"

# Output directories
VEC_00_14_DIR = ensure_dir(OUTPUT_PATH / "Vec_00_14")

# Output shapefile with results
OUTPUT_SHP = OUTPUT_PATH / "Boundaries_MT_2000_2014.shp"

# Minimum area threshold for new patches (in m²)
MIN_AREA_THRESHOLD = 100


# =============================================================================
# Helper Functions
# =============================================================================

def classify_temporal_change(gdf_t1, gdf_t2):
    """
    Create a change map by combining T1 and T2 layers.

    Uses an optimized approach with unary_union to avoid expensive
    polygon-by-polygon overlay operations.

    Classifies each patch as:
    - 'Unchanged': exists in both T1 and T2
    - 'New': exists only in T2
    - 'Lost': exists only in T1

    Parameters
    ----------
    gdf_t1 : GeoDataFrame
        Built-up areas at T1 (2000)
    gdf_t2 : GeoDataFrame
        Built-up areas at T2 (2014)

    Returns
    -------
    GeoDataFrame
        Combined T1 and T2 with temporal classification
    """
    from shapely.geometry import MultiPolygon
    from shapely.validation import make_valid

    # Create unified geometries for faster operations
    print("    Creating unified geometries...")
    t1_union = unary_union(gdf_t1.geometry) if len(gdf_t1) > 0 else None
    t2_union = unary_union(gdf_t2.geometry) if len(gdf_t2) > 0 else None

    results = []

    # New areas: T2 - T1 (areas in T2 but not in T1)
    if t2_union and t1_union:
        print("    Computing new areas (T2 - T1)...")
        new_geom = t2_union.difference(t1_union)
        new_geom = make_valid(new_geom)
        if not new_geom.is_empty:
            # Convert to list of polygons
            if new_geom.geom_type == 'Polygon':
                new_polys = [new_geom]
            elif new_geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
                new_polys = [g for g in new_geom.geoms if g.geom_type == 'Polygon' and not g.is_empty]
            else:
                new_polys = []
            for poly in new_polys:
                results.append({
                    'geometry': poly,
                    'Area': poly.area,
                    'Perim': poly.length,
                    'Temp_Class': 'New'
                })
    elif t2_union:
        # All T2 is new
        if t2_union.geom_type == 'Polygon':
            new_polys = [t2_union]
        else:
            new_polys = [g for g in t2_union.geoms if g.geom_type == 'Polygon']
        for poly in new_polys:
            results.append({
                'geometry': poly,
                'Area': poly.area,
                'Perim': poly.length,
                'Temp_Class': 'New'
            })

    # Unchanged areas: T1 ∩ T2 (areas in both)
    if t1_union and t2_union:
        print("    Computing unchanged areas (T1 ∩ T2)...")
        unchanged_geom = t1_union.intersection(t2_union)
        unchanged_geom = make_valid(unchanged_geom)
        if not unchanged_geom.is_empty:
            if unchanged_geom.geom_type == 'Polygon':
                unchanged_polys = [unchanged_geom]
            elif unchanged_geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
                unchanged_polys = [g for g in unchanged_geom.geoms if g.geom_type == 'Polygon' and not g.is_empty]
            else:
                unchanged_polys = []
            for poly in unchanged_polys:
                results.append({
                    'geometry': poly,
                    'Area': poly.area,
                    'Perim': poly.length,
                    'Temp_Class': 'Unchanged'
                })

    # Lost areas: T1 - T2 (areas in T1 but not in T2)
    if t1_union and t2_union:
        print("    Computing lost areas (T1 - T2)...")
        lost_geom = t1_union.difference(t2_union)
        lost_geom = make_valid(lost_geom)
        if not lost_geom.is_empty:
            if lost_geom.geom_type == 'Polygon':
                lost_polys = [lost_geom]
            elif lost_geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
                lost_polys = [g for g in lost_geom.geoms if g.geom_type == 'Polygon' and not g.is_empty]
            else:
                lost_polys = []
            for poly in lost_polys:
                results.append({
                    'geometry': poly,
                    'Area': poly.area,
                    'Perim': poly.length,
                    'Temp_Class': 'Lost'
                })

    # Create GeoDataFrame
    if results:
        change_gdf = gpd.GeoDataFrame(results, crs=gdf_t2.crs)
    else:
        change_gdf = gpd.GeoDataFrame(
            columns=['geometry', 'Area', 'Perim', 'Temp_Class'],
            crs=gdf_t2.crs
        )

    return change_gdf


def calc_lei_for_new_patches(change_gdf):
    """
    Calculate Landscape Expansion Index for new patches.

    LEI = (perimeter - shared_boundary) / perimeter

    Parameters
    ----------
    change_gdf : GeoDataFrame
        Change map with Temp_Class column

    Returns
    -------
    GeoDataFrame
        Updated GeoDataFrame with LEI and Growth_t columns
    """
    change_gdf['LEI'] = 0.0
    change_gdf['Growth_t'] = ''

    # Get unchanged/existing urban area
    existing = change_gdf[change_gdf['Temp_Class'] == 'Unchanged']
    if len(existing) == 0:
        # No unchanged areas, all new patches are outlying
        new_mask = change_gdf['Temp_Class'] == 'New'
        change_gdf.loc[new_mask, 'Growth_t'] = 'Outlying'
        return change_gdf

    existing_union = unary_union(existing.geometry)

    # Calculate LEI for each new patch
    new_patches = change_gdf[change_gdf['Temp_Class'] == 'New'].copy()

    for idx in new_patches.index:
        geom = change_gdf.loc[idx, 'geometry']
        perimeter = geom.length

        if perimeter == 0:
            change_gdf.loc[idx, 'LEI'] = 0.0
            change_gdf.loc[idx, 'Growth_t'] = 'Outlying'
            continue

        # Calculate shared boundary with existing urban
        boundary = geom.boundary
        intersection = boundary.intersection(existing_union.boundary)
        shared_length = intersection.length if not intersection.is_empty else 0

        # LEI = shared_boundary / perimeter
        # LEI = 0: Outlying (no shared boundary)
        # LEI = 0-0.5: Edge-Expansive
        # LEI > 0.5: Infilling
        lei = shared_length / perimeter
        change_gdf.loc[idx, 'LEI'] = lei
        change_gdf.loc[idx, 'Growth_t'] = classify_growth_type(lei)

    # Handle edge case: patches that touch only at corners
    # These should be Edge-Expansive, not Outlying
    outlying = change_gdf[(change_gdf['Growth_t'] == 'Outlying') &
                          (change_gdf['Temp_Class'] == 'New')]

    if len(outlying) > 0 and len(existing) > 0:
        # Check for point intersection (corner touch)
        non_outlying = change_gdf[
            (change_gdf['Temp_Class'] == 'Unchanged') |
            (change_gdf['Growth_t'].isin(['Edge-Expansive', 'Infilling']))
        ]
        non_outlying_union = unary_union(non_outlying.geometry)

        for idx in outlying.index:
            geom = change_gdf.loc[idx, 'geometry']
            intersection = geom.intersection(non_outlying_union)
            # If there's any intersection (even a point), it's edge-expansive
            if not intersection.is_empty:
                change_gdf.loc[idx, 'Growth_t'] = 'Edge-Expansive'

    return change_gdf


def calc_awmai(new_patches_gdf, roads_gdf, total_new_area):
    """
    Calculate Area-Weighted Mean Accessibility Index.

    AWMAI considers distance to roads for outlying patches and
    area proportion for adjacent patches.

    Parameters
    ----------
    new_patches_gdf : GeoDataFrame
        New urban patches with Growth_t classification
    roads_gdf : GeoDataFrame
        Road network
    total_new_area : float
        Total area of new urban development

    Returns
    -------
    float
        AWMAI value
    """
    if len(new_patches_gdf) == 0 or total_new_area == 0:
        return 0.0

    if len(roads_gdf) == 0:
        return 0.0

    # Separate outlying and adjacent (edge-expansive + infilling) patches
    outlying = new_patches_gdf[new_patches_gdf['Growth_t'] == 'Outlying']
    adjacent = new_patches_gdf[new_patches_gdf['Growth_t'].isin(['Edge-Expansive', 'Infilling'])]

    roads_union = unary_union(roads_gdf.geometry)

    # Calculate weighted distance for outlying patches
    weighted_dist_out = 0.0
    for idx, row in outlying.iterrows():
        distance = row.geometry.distance(roads_union)
        area = row.geometry.area
        # Weight: (area * 100) / ((distance + 1) * total_new_area)
        weighted_dist_out += (area * 100) / ((distance + 1) * total_new_area)

    # Calculate weighted area for adjacent patches
    weighted_area_adj = 0.0
    for idx, row in adjacent.iterrows():
        area = row.geometry.area
        weighted_area_adj += (area * 100) / total_new_area

    awmai = weighted_dist_out + weighted_area_adj
    return awmai


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
    gdf['UCR'] = np.nan    # Urban Change Rate
    gdf['AWMEI'] = np.nan  # Area-Weighted Mean Expansion Index
    gdf['AWMAI'] = np.nan  # Area-Weighted Mean Accessibility Index

    return gdf


def process_fua(fua_code, results_gdf):
    """
    Process a single FUA and calculate multi-temporal metrics.

    Parameters
    ----------
    fua_code : str
        FUA code identifier
    results_gdf : GeoDataFrame
        Results GeoDataFrame to update

    Returns
    -------
    dict
        Dictionary with calculated metrics
    """
    metrics = {
        'fuacode_si': fua_code,
        'UCR': np.nan,
        'AWMEI': np.nan,
        'AWMAI': np.nan
    }

    try:
        # =================================================================
        # Step 1: Find input files from Steps 1 and 2
        # =================================================================
        print(f"  Loading T1 and T2 data...")

        # Find T1 (2000) file
        t1_files = list(VEC_00_DIR.glob(f"BUILT_{fua_code}_2000_*.shp"))
        if not t1_files:
            print(f"  WARNING: T1 file not found. Run Step 1 first.")
            return metrics

        # Find T2 (2014) file
        t2_files = list(VEC_14_DIR.glob(f"BUILT_{fua_code}_2014_*.shp"))
        if not t2_files:
            print(f"  WARNING: T2 file not found. Run Step 2 first.")
            return metrics

        gdf_t1 = gpd.read_file(t1_files[0])
        gdf_t2 = gpd.read_file(t2_files[0])

        # Ensure Area column exists
        if 'Area' not in gdf_t1.columns:
            gdf_t1['Area'] = gdf_t1.geometry.area
        if 'Area' not in gdf_t2.columns:
            gdf_t2['Area'] = gdf_t2.geometry.area

        # =================================================================
        # Step 2: Calculate Urban Change Rate (UCR)
        # =================================================================
        print(f"  Calculating UCR...")

        area_t1 = gdf_t1.geometry.area.sum()
        area_t2 = gdf_t2.geometry.area.sum()

        if area_t1 > 0:
            ucr = ((area_t2 - area_t1) / area_t1) * 100
            metrics['UCR'] = ucr
            print(f"    UCR: {ucr:.2f}%")

        # =================================================================
        # Step 3: Create change map and classify
        # =================================================================
        print(f"  Creating change map...")

        change_gdf = classify_temporal_change(gdf_t1, gdf_t2)

        # Save change map
        output_change = VEC_00_14_DIR / f"BUILT_{fua_code}_00_14.shp"
        change_gdf.to_file(output_change)

        # =================================================================
        # Step 4: Calculate LEI and classify growth types
        # =================================================================
        print(f"  Calculating LEI and classifying growth...")

        change_gdf = calc_lei_for_new_patches(change_gdf)

        # Filter new patches above threshold
        new_patches = change_gdf[
            (change_gdf['Temp_Class'] == 'New') &
            (change_gdf['Area'] > MIN_AREA_THRESHOLD)
        ]

        if len(new_patches) == 0:
            print(f"  No new patches found.")
            # Save updated change map
            change_gdf.to_file(output_change)
            return metrics

        total_new_area = new_patches.geometry.area.sum()

        # =================================================================
        # Step 5: Calculate AWMEI
        # =================================================================
        print(f"  Calculating AWMEI...")

        # AWMEI = sum(LEI_i * (area_i / total_new_area) * 100)
        awmei = 0.0
        for idx, row in new_patches.iterrows():
            lei = row['LEI']
            area = row.geometry.area
            awmei += lei * (area / total_new_area) * 100

        metrics['AWMEI'] = awmei
        print(f"    AWMEI: {awmei:.2f}")

        # =================================================================
        # Step 6: Calculate AWMAI
        # =================================================================
        print(f"  Calculating AWMAI...")

        # Find road network file
        road_files = list(ROADS_PJ_DIR.glob(f"ROAD_{fua_code}_*.shp"))

        if road_files:
            roads_gdf = gpd.read_file(road_files[0])

            # Ensure same CRS
            if roads_gdf.crs != new_patches.crs:
                roads_gdf = roads_gdf.to_crs(new_patches.crs)

            awmai = calc_awmai(new_patches, roads_gdf, total_new_area)
            metrics['AWMAI'] = awmai
            print(f"    AWMAI: {awmai:.2f}")
        else:
            print(f"    WARNING: Road network not found. AWMAI not calculated.")

        # Save updated change map with growth types
        change_gdf.to_file(output_change)

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
        description='Calculate multi-temporal urban growth metrics (2000-2014).'
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
    print("Step 5: Multi-Temporal Metrics (2000-2014)")
    print("=" * 60)

    # Check for required inputs
    if not VEC_00_DIR.exists() or len(list(VEC_00_DIR.glob("*.shp"))) == 0:
        print(f"\nERROR: Step 1 outputs not found at:\n{VEC_00_DIR}")
        print("\nPlease run Step 1 first.")
        sys.exit(1)

    if not VEC_14_DIR.exists() or len(list(VEC_14_DIR.glob("*.shp"))) == 0:
        print(f"\nERROR: Step 2 outputs not found at:\n{VEC_14_DIR}")
        print("\nPlease run Step 2 first.")
        sys.exit(1)

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

        # Process FUA
        metrics = process_fua(fua_code, results_gdf)

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
    OUTPUT_CSV = OUTPUT_PATH / "Boundaries_MT_2000_2014.csv"
    csv_cols = ['fuacode_si', 'UCR', 'AWMEI', 'AWMAI']
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
