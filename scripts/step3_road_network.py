"""
Step 3: Road Network Density Metrics

Open-source Python 3 implementation of the original ArcPy script.
Calculates road network density for each FUA using GRIP dataset.

Reference: Sapena et al. (2020) https://doi.org/10.3390/ijgi9070436
Data source GRIP: https://www.globio.info/download-grip-dataset

Required: GRIP road network shapefiles must be downloaded and placed in data_external/GRIP/

Usage:
    python step3_road_network.py                    # Process all FUAs
    python step3_road_network.py --country USA      # Process only USA FUAs
    python step3_road_network.py --country USA --workers 4  # Parallel processing
"""

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import geopandas as gpd
import numpy as np
import pandas as pd

from utils import BOUNDARIES_PATH as BOUNDARIES_DIR

# Import local utilities
from utils import DATA_EXTERNAL_PATH, OUTPUT_PATH, ensure_dir
from utils import UTM_ZONES_PATH as UTM_ZONES_DIR

# =============================================================================
# Configuration
# =============================================================================

# Input paths
BOUNDARIES_4326_PATH = BOUNDARIES_DIR / "Boundaries_4326.shp"
BOUNDARIES_3857_PATH = BOUNDARIES_DIR / "Boundaries_3857.shp"
UTM_ZONES_PATH = UTM_ZONES_DIR / "UTM_Zone_EPSG_4326.shp"
FUA_DIR = OUTPUT_PATH / "FUAs"

# GRIP road network data directory
# Download from: https://www.globio.info/download-grip-dataset
GRIP_PATH = DATA_EXTERNAL_PATH / "GRIP"

# Output directories (created in main() before processing)
ROADS_DIR = OUTPUT_PATH / "ROADs"
ROADS_PJ_DIR = OUTPUT_PATH / "ROADs_PJ"

# Output shapefile with results
OUTPUT_SHP = OUTPUT_PATH / "Boundaries_ROADs.shp"


# =============================================================================
# Helper Functions
# =============================================================================

def calc_road_density(roads_gdf, area_km2):
    """
    Calculate road network density.

    Parameters
    ----------
    roads_gdf : GeoDataFrame
        Road network within FUA
    area_km2 : float
        FUA area in km²

    Returns
    -------
    float
        Road density in km/km²
    """
    if len(roads_gdf) == 0 or area_km2 == 0:
        return 0.0

    # Total road length in km
    total_length_km = roads_gdf.geometry.length.sum() / 1000

    # Density
    return total_length_km / area_km2


def clip_roads_fast(roads_gdf, fua_geometry):
    """
    Fast road clipping using spatial indexing and intersection.

    Parameters
    ----------
    roads_gdf : GeoDataFrame
        Roads within bounding box
    fua_geometry : shapely geometry
        FUA boundary polygon

    Returns
    -------
    GeoDataFrame
        Roads clipped to FUA boundary
    """
    if len(roads_gdf) == 0:
        return roads_gdf

    # Build spatial index and find candidate roads
    roads_gdf = roads_gdf.copy()
    possible_matches_idx = list(roads_gdf.sindex.intersection(fua_geometry.bounds))
    if not possible_matches_idx:
        return roads_gdf.iloc[0:0]  # Empty GeoDataFrame with same schema

    candidates = roads_gdf.iloc[possible_matches_idx]

    # Filter to roads that actually intersect
    mask = candidates.geometry.intersects(fua_geometry)
    intersecting = candidates[mask].copy()

    if len(intersecting) == 0:
        return roads_gdf.iloc[0:0]

    # Clip geometries to FUA boundary
    intersecting['geometry'] = intersecting.geometry.intersection(fua_geometry)

    # Remove empty geometries
    intersecting = intersecting[~intersecting.geometry.is_empty]

    return intersecting


def find_grip_files(grip_path):
    """
    Find all GRIP shapefile directories.

    Parameters
    ----------
    grip_path : Path
        Path to GRIP data directory

    Returns
    -------
    list
        List of paths to GRIP shapefiles
    """
    grip_files = []

    if not grip_path.exists():
        return grip_files

    # GRIP data is organized in folders like "GRIP4_region1_shp"
    for folder in grip_path.iterdir():
        if folder.is_dir() and folder.name.endswith("_shp"):
            # Find .shp file in folder
            shp_files = list(folder.glob("*.shp"))
            if shp_files:
                grip_files.append(shp_files[0])

    return grip_files


def fua_intersects_grip_extent(fua_geometry, grip_gdf):
    """
    Check if FUA intersects the extent of a GRIP dataset.

    Parameters
    ----------
    fua_geometry : shapely geometry
        FUA boundary
    grip_gdf : GeoDataFrame
        GRIP road network (or just its bounds)

    Returns
    -------
    bool
        True if FUA is within GRIP extent
    """
    grip_bounds = grip_gdf.total_bounds  # minx, miny, maxx, maxy
    fua_bounds = fua_geometry.bounds

    # Check if FUA is within GRIP extent
    return (fua_bounds[0] >= grip_bounds[0] and
            fua_bounds[1] >= grip_bounds[1] and
            fua_bounds[2] <= grip_bounds[2] and
            fua_bounds[3] <= grip_bounds[3])


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
    gdf = gpd.read_file(BOUNDARIES_3857_PATH)

    # Add metric fields
    gdf['AreaFUA'] = np.nan
    gdf['D_road'] = np.nan  # Road density in km/km²

    return gdf


def process_fua(fua_code, fua_4326, grip_files, utm_zones_gdf, results_gdf):
    """
    Process a single FUA and calculate road density.

    Parameters
    ----------
    fua_code : str
        FUA code identifier
    fua_4326 : GeoDataFrame
        FUA boundary in EPSG:4326
    grip_files : list
        List of GRIP shapefile paths
    utm_zones_gdf : GeoDataFrame
        UTM zones for EPSG lookup
    results_gdf : GeoDataFrame
        Results GeoDataFrame to update

    Returns
    -------
    dict
        Dictionary with calculated metrics
    """
    metrics = {
        'fuacode_si': fua_code,
        'AreaFUA': np.nan,
        'D_road': np.nan
    }

    try:
        fua_geometry = fua_4326.geometry.iloc[0]

        # =================================================================
        # Step 1: Find ALL GRIP files that contain roads for this FUA
        # =================================================================
        print("  Finding GRIP data for FUA...")

        all_roads = []
        for grip_path in grip_files:
            # Read roads within FUA bbox from this GRIP file
            grip_bounds = gpd.read_file(grip_path, bbox=fua_geometry.bounds)

            if len(grip_bounds) > 0:
                print(f"    Found {len(grip_bounds)} roads in {grip_path.name}")
                all_roads.append(grip_bounds)

        if not all_roads:
            print("  No GRIP data found for this FUA.")
            return metrics

        # Combine roads from all matching GRIP files
        if len(all_roads) == 1:
            grip_gdf = all_roads[0]
        else:
            grip_gdf = pd.concat(all_roads, ignore_index=True)
            print(f"  Combined {len(grip_gdf)} roads from {len(all_roads)} GRIP regions")

        # =================================================================
        # Step 2: Clip roads to FUA boundary (optimized with spatial indexing)
        # =================================================================
        print(f"  Clipping {len(grip_gdf)} road segments...")

        # Use optimized clipping with spatial indexing
        roads_clipped = clip_roads_fast(grip_gdf, fua_geometry)

        if len(roads_clipped) == 0:
            print("  No roads after clipping.")
            return metrics

        print(f"  Clipped to {len(roads_clipped)} road segments")

        # Save clipped roads in WGS84
        output_4326 = ROADS_DIR / f"ROADS_{fua_code}_4326.shp"
        roads_clipped.to_file(output_4326)

        # =================================================================
        # Step 3: Project to UTM
        # =================================================================
        print("  Projecting to UTM...")

        # Get UTM zone
        centroid = fua_geometry.centroid
        epsg = None

        for _idx, row in utm_zones_gdf.iterrows():
            if row.geometry.contains(centroid):
                epsg = int(row['EPSG'])
                break

        if epsg is None:
            # Fallback: calculate UTM zone
            lon, lat = centroid.x, centroid.y
            zone = int((lon + 180) / 6) + 1
            epsg = 32600 + zone if lat >= 0 else 32700 + zone

        print(f"  Using EPSG:{epsg}")

        # Project roads
        roads_utm = roads_clipped.to_crs(f"EPSG:{epsg}")

        # Save projected roads
        output_utm = ROADS_PJ_DIR / f"ROAD_{fua_code}_{epsg}.shp"
        roads_utm.to_file(output_utm)

        # =================================================================
        # Step 4: Get FUA area from Step 1
        # =================================================================
        # Look for FUA file from step 1
        fua_files = list(FUA_DIR.glob(f"FUA_{fua_code}_*.shp"))
        if fua_files:
            fua_utm = gpd.read_file(fua_files[0])
            area_km2 = fua_utm.geometry.area.sum() / 1_000_000
        else:
            # Fallback: project FUA and calculate
            fua_utm = fua_4326.to_crs(f"EPSG:{epsg}")
            area_km2 = fua_utm.geometry.area.sum() / 1_000_000

        metrics['AreaFUA'] = area_km2

        # =================================================================
        # Step 5: Calculate road density
        # =================================================================
        print("  Calculating road density...")

        density = calc_road_density(roads_utm, area_km2)
        metrics['D_road'] = density

        print(f"  Road density: {density:.2f} km/km²")

    except Exception as e:
        print(f"  ERROR processing FUA {fua_code}: {e}")
        import traceback
        traceback.print_exc()

    return metrics


def process_fua_wrapper(args):
    """Wrapper for parallel processing."""
    fua_code, fua_4326_dict, grip_files, utm_zones_path = args

    # Reconstruct GeoDataFrame from dict (needed for multiprocessing)
    fua_4326 = gpd.GeoDataFrame.from_dict(fua_4326_dict)
    fua_4326 = fua_4326.set_crs("EPSG:4326")

    # Load UTM zones (each worker needs its own copy)
    utm_zones = gpd.read_file(utm_zones_path)

    return process_fua(fua_code, fua_4326, grip_files, utm_zones, None)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate road network density for FUAs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python step3_road_network.py                    # Process all FUAs
  python step3_road_network.py --country USA      # Process only USA FUAs
  python step3_road_network.py --country USA --workers 4  # Parallel processing
        """
    )
    parser.add_argument(
        "--country",
        type=str,
        default=None,
        help="Filter FUAs by country code prefix (e.g., USA, AUS, CHN)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of FUAs to process (for testing)"
    )
    return parser.parse_args()


def main():
    """Main processing function."""
    args = parse_args()

    start_time = time.time()
    print("=" * 60)
    print("Step 3: Road Network Density Metrics")
    if args.country:
        print(f"  Country filter: {args.country}")
    if args.workers > 1:
        print(f"  Parallel workers: {args.workers}")
    print("=" * 60)

    # Check for GRIP data
    grip_files = find_grip_files(GRIP_PATH)

    if len(grip_files) == 0:
        print(f"\nERROR: GRIP road data not found at:\n{GRIP_PATH}")
        print("\nPlease download GRIP data from:")
        print("  https://www.globio.info/download-grip-dataset")
        print("\nExtract the regional shapefiles to data_external/GRIP/")
        sys.exit(1)

    print(f"\nFound {len(grip_files)} GRIP datasets")

    # Ensure output directories exist before writing
    for d in (OUTPUT_PATH, ROADS_DIR, ROADS_PJ_DIR):
        ensure_dir(d)

    # Initialize output
    results_gdf = initialize_output_shapefile()

    # Load boundaries in WGS84
    print("\nLoading FUA boundaries...")
    boundaries_4326 = gpd.read_file(BOUNDARIES_4326_PATH)

    # Load UTM zones
    print("Loading UTM zones...")
    utm_zones = gpd.read_file(UTM_ZONES_PATH)

    # Get list of FUAs (exclude FR030 as in original script)
    fua_codes = [code for code in results_gdf['fuacode_si'].tolist() if code != 'FR030']

    # Apply country filter if specified
    if args.country:
        fua_codes = [code for code in fua_codes if code.startswith(args.country)]
        print(f"\nFiltered to {len(fua_codes)} {args.country} FUAs")

    # Apply limit if specified
    if args.limit:
        fua_codes = fua_codes[:args.limit]
        print(f"Limited to first {args.limit} FUAs")

    n_fuas = len(fua_codes)
    print(f"\nProcessing {n_fuas} FUAs...")

    # Process FUAs
    if args.workers > 1:
        # Parallel processing
        print(f"\nUsing {args.workers} parallel workers...")

        # Prepare arguments for workers
        work_items = []
        for fua_code in fua_codes:
            fua_4326 = boundaries_4326[boundaries_4326['fuacode_si'] == fua_code].copy()
            if len(fua_4326) > 0:
                # Convert to dict for pickling
                fua_dict = {
                    'geometry': fua_4326.geometry.tolist(),
                    'fuacode_si': fua_4326['fuacode_si'].tolist()
                }
                work_items.append((fua_code, fua_dict, grip_files, UTM_ZONES_PATH))

        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(process_fua_wrapper, item): item[0] for item in work_items}

            for future in as_completed(futures):
                fua_code = futures[future]
                completed += 1
                try:
                    metrics = future.result()
                    # Update results
                    idx = results_gdf[results_gdf['fuacode_si'] == fua_code].index[0]
                    for key, value in metrics.items():
                        if key in results_gdf.columns:
                            results_gdf.loc[idx, key] = value
                    print(f"[{completed}/{n_fuas}] {fua_code}: D_road={metrics.get('D_road', 'N/A'):.2f} km/km²")
                except Exception as e:
                    print(f"[{completed}/{n_fuas}] {fua_code}: ERROR - {e}")
    else:
        # Sequential processing
        for i, fua_code in enumerate(fua_codes):
            fua_start = time.time()
            print(f"\n[{i+1}/{n_fuas}] Processing FUA: {fua_code}")

            # Get FUA boundary in WGS84
            fua_4326 = boundaries_4326[boundaries_4326['fuacode_si'] == fua_code].copy()

            if len(fua_4326) == 0:
                print("  WARNING: FUA not found in boundaries. Skipping...")
                continue

            # Process FUA
            metrics = process_fua(fua_code, fua_4326, grip_files, utm_zones, results_gdf)

            # Update results
            idx = results_gdf[results_gdf['fuacode_si'] == fua_code].index[0]
            for key, value in metrics.items():
                if key in results_gdf.columns:
                    results_gdf.loc[idx, key] = value

            elapsed = time.time() - fua_start
            print(f"  Time: {elapsed:.1f} sec")

    # Save results
    output_path = OUTPUT_SHP
    if args.country:
        # Save to country-specific file
        output_path = OUTPUT_PATH / f"Boundaries_ROADs_{args.country}.shp"

    print(f"\nSaving results to {output_path}...")

    # Filter results to processed FUAs if country filter was used
    if args.country:
        results_gdf = results_gdf[results_gdf['fuacode_si'].str.startswith(args.country)]

    results_gdf.to_file(output_path)

    # Print summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("Processing complete!")
    print(f"Total time: {total_time/60:.2f} minutes")
    print(f"FUAs processed: {n_fuas}")
    print(f"Output: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
