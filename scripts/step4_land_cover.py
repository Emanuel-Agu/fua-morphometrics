"""
Step 4: Land Cover Metrics from CCI-LC

Open-source Python 3 implementation of the original ArcPy script.
Processes ESA CCI Land Cover data and calculates land cover densities
and change percentages for each FUA.

Reference: Sapena et al. (2020) https://doi.org/10.3390/ijgi9070436
Data source CCI-LC: ftp://anon-ftp.ceda.ac.uk/neodc/esacci/

Required: CCI Land Cover data must be downloaded and placed in data_external/CCI_LC/
"""

import argparse
import sys
import time

import geopandas as gpd
import numpy as np
import rasterio

from utils import BOUNDARIES_PATH as BOUNDARIES_DIR

# Import local utilities
from utils import DATA_EXTERNAL_PATH, OUTPUT_PATH, ensure_dir, polygonize_raster
from utils import UTM_ZONES_PATH as UTM_ZONES_DIR

# =============================================================================
# Configuration
# =============================================================================

# Input paths
BOUNDARIES_4326_PATH = BOUNDARIES_DIR / "Boundaries_4326.shp"
BOUNDARIES_3857_PATH = BOUNDARIES_DIR / "Boundaries_3857.shp"
UTM_ZONES_PATH = UTM_ZONES_DIR / "UTM_Zone_EPSG_4326.shp"
FUA_DIR = OUTPUT_PATH / "FUAs"

# CCI Land Cover data
# Download from: ftp://anon-ftp.ceda.ac.uk/neodc/esacci/
CCI_LC_DIR = DATA_EXTERNAL_PATH / "CCI_LC"

# Option 1: Multi-temporal file (single file with bands for each year 1992-2015)
CCI_LC_MULTITEMPORAL = CCI_LC_DIR / "ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992_2015-v2.0.7.tif"

# Option 2: Single-year files
CCI_LC_SINGLE_YEAR = {
    2000: CCI_LC_DIR / "ESACCI-LC-L4-LCCS-Map-300m-P1Y-2000-v2.0.7.tif",
    2014: CCI_LC_DIR / "ESACCI-LC-L4-LCCS-Map-300m-P1Y-2014-v2.0.7.tif"
}

# Band indices for multi-temporal file (1-indexed, year = 1992 + band - 1)
CCI_LC_BANDS = {
    2000: 9,   # Band 9 = year 2000
    2014: 23   # Band 23 = year 2014
}

# Output directories (created in main() before processing)
CCI_4326_DIR = OUTPUT_PATH / "CCI_4326"
VEC_CCI_DIR = OUTPUT_PATH / "Vec_CCI"

# Output shapefile with results
OUTPUT_SHP = OUTPUT_PATH / "Boundaries_CCI_LC.shp"

# Land cover reclassification
# Original CCI classes -> 7 aggregated classes
# 1 = Agriculture (10-30)
# 2 = High vegetation / Forest (40-100, 160-180)
# 3 = Low vegetation / Shrub/Grass (110-153)
# 4 = Urban (190)
# 5 = Bare/Sparse (200-202)
# 6 = Water (210)
# 7 = Snow/Ice (220)
RECLASS_CCI = {
    (10, 30): 1,      # Agriculture
    (40, 100): 2,     # Forest/High vegetation
    (110, 153): 3,    # Shrub/Grass/Low vegetation
    (160, 180): 2,    # Additional forest classes
    190: 4,           # Urban
    (200, 202): 5,    # Bare/Sparse
    210: 6,           # Water
    220: 7,           # Snow/Ice
}


# =============================================================================
# CCI Data Format Detection
# =============================================================================

def detect_cci_format():
    """
    Detect which CCI Land Cover data format is available.

    Returns
    -------
    tuple
        (format_type, data_source) where:
        - format_type: 'multitemporal' or 'single_year'
        - data_source: path to multi-temporal file or dict of single-year files
    """
    # Check for multi-temporal file first (preferred)
    if CCI_LC_MULTITEMPORAL.exists():
        return 'multitemporal', CCI_LC_MULTITEMPORAL

    # Check for single-year files
    available_years = {
        year: path for year, path in CCI_LC_SINGLE_YEAR.items()
        if path.exists()
    }

    if len(available_years) == len(CCI_LC_SINGLE_YEAR):
        return 'single_year', available_years

    # Partial availability
    if available_years:
        return 'single_year', available_years

    return None, None


def check_cci_data():
    """
    Check CCI data availability and print status.

    Returns
    -------
    tuple or None
        (format_type, data_source) if data available, None otherwise
    """
    format_type, data_source = detect_cci_format()

    if format_type == 'multitemporal':
        print(f"  Found multi-temporal CCI file: {CCI_LC_MULTITEMPORAL.name}")
        return format_type, data_source

    elif format_type == 'single_year':
        print("  Found single-year CCI files:")
        for year, path in data_source.items():
            print(f"    {year}: {path.name}")
        return format_type, data_source

    else:
        print("\nERROR: No CCI Land Cover data found.")
        print("\nExpected one of:")
        print(f"  Multi-temporal: {CCI_LC_MULTITEMPORAL}")
        print("  Or single-year files:")
        for year, path in CCI_LC_SINGLE_YEAR.items():
            print(f"    {year}: {path}")
        print("\nDownload from: ftp://anon-ftp.ceda.ac.uk/neodc/esacci/")
        return None, None


# =============================================================================
# Helper Functions
# =============================================================================

def extract_band_to_file(input_path, band_index, output_path):
    """
    Extract a single band from a multi-band raster.

    Parameters
    ----------
    input_path : Path
        Input multi-band raster
    band_index : int
        Band index (1-indexed)
    output_path : Path
        Output single-band raster

    Returns
    -------
    Path
        Path to output raster
    """
    with rasterio.open(input_path) as src:
        data = src.read(band_index)
        meta = src.meta.copy()
        meta.update(count=1)

        with rasterio.open(output_path, 'w', **meta) as dst:
            dst.write(data, 1)

    return output_path


def reclassify_cci(raster_path, output_path):
    """
    Reclassify CCI land cover to 7 classes.

    Parameters
    ----------
    raster_path : Path
        Input CCI raster
    output_path : Path
        Output reclassified raster

    Returns
    -------
    Path
        Path to output raster
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        out_data = np.zeros_like(data, dtype=np.uint8)

        # Apply reclassification
        # Agriculture (10-30)
        out_data[(data >= 10) & (data <= 30)] = 1
        # Forest (40-100)
        out_data[(data >= 40) & (data <= 100)] = 2
        # Shrub/Grass (110-153)
        out_data[(data >= 110) & (data <= 153)] = 3
        # Additional forest (160-180)
        out_data[(data >= 160) & (data <= 180)] = 2
        # Urban (190)
        out_data[data == 190] = 4
        # Bare (200-202)
        out_data[(data >= 200) & (data <= 202)] = 5
        # Water (210)
        out_data[data == 210] = 6
        # Snow/Ice (220)
        out_data[data == 220] = 7

        meta = src.meta.copy()
        meta.update(dtype=rasterio.uint8, nodata=0)

        with rasterio.open(output_path, 'w', **meta) as dst:
            dst.write(out_data, 1)

    return output_path


def calc_lc_density(gdf, class_value, total_area_km2):
    """
    Calculate land cover density for a specific class.

    Parameters
    ----------
    gdf : GeoDataFrame
        Polygonized land cover
    class_value : int
        Land cover class value (1-7)
    total_area_km2 : float
        Total FUA area in km²

    Returns
    -------
    float
        Land cover density as percentage
    """
    if len(gdf) == 0 or total_area_km2 == 0:
        return 0.0

    class_gdf = gdf[gdf['DN'] == class_value]
    if len(class_gdf) == 0:
        return 0.0

    class_area_km2 = class_gdf.geometry.area.sum() / 1_000_000
    return (class_area_km2 / total_area_km2) * 100


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

    # Add metric fields for each land cover class (7 classes)
    # D_LCx_T1 = Density at T1 (2000)
    # D_LCx_T2 = Density at T2 (2014)
    # CP_LCx = Change percentage
    for i in range(1, 8):
        gdf[f'D_LC{i}_T1'] = np.nan
        gdf[f'D_LC{i}_T2'] = np.nan
        gdf[f'CP_LC{i}'] = np.nan

    return gdf


def process_fua(fua_code, fua_4326, utm_zones_gdf, results_gdf, cci_format='single_year', cci_data=None):
    """
    Process a single FUA and calculate land cover metrics.

    Parameters
    ----------
    fua_code : str
        FUA code identifier
    fua_4326 : GeoDataFrame
        FUA boundary in EPSG:4326
    utm_zones_gdf : GeoDataFrame
        UTM zones for EPSG lookup
    results_gdf : GeoDataFrame
        Results GeoDataFrame to update
    cci_format : str
        'multitemporal' or 'single_year'
    cci_data : Path or dict
        Path to multi-temporal file or dict of single-year file paths

    Returns
    -------
    dict
        Dictionary with calculated metrics
    """
    metrics = {'fuacode_si': fua_code}

    # Initialize all metrics to NaN
    for i in range(1, 8):
        metrics[f'D_LC{i}_T1'] = np.nan
        metrics[f'D_LC{i}_T2'] = np.nan
        metrics[f'CP_LC{i}'] = np.nan

    try:
        fua_geometry = fua_4326.geometry.iloc[0]

        # =================================================================
        # Step 1: Get UTM zone
        # =================================================================
        print("  Determining UTM zone...")
        centroid = fua_geometry.centroid
        epsg = None

        for _idx, row in utm_zones_gdf.iterrows():
            if row.geometry.contains(centroid):
                epsg = int(row['EPSG'])
                break

        if epsg is None:
            lon, lat = centroid.x, centroid.y
            zone = int((lon + 180) / 6) + 1
            epsg = 32600 + zone if lat >= 0 else 32700 + zone

        print(f"  Using EPSG:{epsg}")

        # Get FUA area
        fua_files = list(FUA_DIR.glob(f"FUA_{fua_code}_*.shp"))
        if fua_files:
            fua_utm = gpd.read_file(fua_files[0])
            area_km2 = fua_utm.geometry.area.sum() / 1_000_000
        else:
            fua_utm = fua_4326.to_crs(f"EPSG:{epsg}")
            area_km2 = fua_utm.geometry.area.sum() / 1_000_000

        # =================================================================
        # Step 2: Process each time period (2000 and 2014)
        # =================================================================
        lc_gdfs = {}

        for date in [2000, 2014]:
            print(f"  Processing year {date}...")

            # Clip CCI to FUA
            output_cci = CCI_4326_DIR / f"CCI_{fua_code}_{date}_4326.tif"

            # Read CCI data based on format type
            from rasterio.mask import mask

            if cci_format == 'multitemporal':
                # Multi-temporal file: extract specific band for the year
                band_index = CCI_LC_BANDS[date]
                with rasterio.open(cci_data) as src:
                    out_image, out_transform = mask(
                        src,
                        [fua_geometry],
                        crop=True,
                        indexes=[band_index]  # Specific band for this year
                    )
                    out_meta = src.meta.copy()

            else:
                # Single-year files
                cci_path = cci_data.get(date) if cci_data else CCI_LC_SINGLE_YEAR.get(date)
                if not cci_path or not cci_path.exists():
                    print(f"  WARNING: CCI file not found for {date}")
                    continue

                with rasterio.open(cci_path) as src:
                    out_image, out_transform = mask(
                        src,
                        [fua_geometry],
                        crop=True,
                        indexes=[1]  # Single-band file
                    )
                    out_meta = src.meta.copy()

            # Write clipped raster
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "count": 1,
                "transform": out_transform
            })

            with rasterio.open(output_cci, 'w', **out_meta) as dst:
                dst.write(out_image[0], 1)

            # Reclassify
            reclass_cci = CCI_4326_DIR / f"LC_{fua_code}_{date}_4326.tif"
            reclassify_cci(output_cci, reclass_cci)

            # Polygonize
            output_vec = CCI_4326_DIR / f"CCI_{fua_code}_{date}_4326.shp"
            lc_gdf = polygonize_raster(reclass_cci, output_vec, crs="EPSG:4326")

            # Project to UTM
            lc_utm = lc_gdf.to_crs(f"EPSG:{epsg}")
            output_vec_utm = VEC_CCI_DIR / f"CCI_{fua_code}_{date}_{epsg}.shp"
            lc_utm.to_file(output_vec_utm)

            lc_gdfs[date] = lc_utm

            # Calculate densities for each class
            suffix = 'T1' if date == 2000 else 'T2'
            for i in range(1, 8):
                density = calc_lc_density(lc_utm, i, area_km2)
                metrics[f'D_LC{i}_{suffix}'] = density

        # =================================================================
        # Step 3: Calculate change percentages
        # =================================================================
        print("  Calculating change percentages...")

        for i in range(1, 8):
            area_t1 = 0.0
            area_t2 = 0.0

            if 2000 in lc_gdfs:
                class_gdf = lc_gdfs[2000][lc_gdfs[2000]['DN'] == i]
                area_t1 = class_gdf.geometry.area.sum() / 1_000_000

            if 2014 in lc_gdfs:
                class_gdf = lc_gdfs[2014][lc_gdfs[2014]['DN'] == i]
                area_t2 = class_gdf.geometry.area.sum() / 1_000_000

            # Change as percentage of FUA area
            metrics[f'CP_LC{i}'] = ((area_t2 - area_t1) / area_km2) * 100

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
        description='Calculate land cover metrics from CCI-LC data for FUAs.'
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
    print("Step 4: Land Cover Metrics from CCI-LC")
    print("=" * 60)

    # Detect and check CCI data format
    print("\nChecking CCI Land Cover data...")
    cci_format, cci_data = check_cci_data()

    if cci_format is None:
        sys.exit(1)

    # Ensure output directories exist before writing
    for d in (OUTPUT_PATH, CCI_4326_DIR, VEC_CCI_DIR):
        ensure_dir(d)

    # Initialize output
    results_gdf = initialize_output_shapefile()

    # Load boundaries in WGS84
    print("\nLoading FUA boundaries...")
    boundaries_4326 = gpd.read_file(BOUNDARIES_4326_PATH)

    # Load UTM zones
    print("Loading UTM zones...")
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

        # Get FUA boundary in WGS84
        fua_4326 = boundaries_4326[boundaries_4326['fuacode_si'] == fua_code].copy()

        if len(fua_4326) == 0:
            print("  WARNING: FUA not found in boundaries. Skipping...")
            continue

        # Process FUA with detected CCI format
        metrics = process_fua(fua_code, fua_4326, utm_zones, results_gdf,
                              cci_format=cci_format, cci_data=cci_data)

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
    OUTPUT_CSV = OUTPUT_PATH / "Boundaries_CCI_LC.csv"
    csv_cols = ['fuacode_si'] + [c for c in processed_gdf.columns
                                  if c.startswith(('D_LC', 'CP_LC'))]
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
