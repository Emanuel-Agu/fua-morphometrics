# -*- coding: utf-8 -*-
"""
Post-processing script to fix SL_UC metrics in existing outputs.

SL_UC should be the largest single connected component of the secondary
urban core, not the sum of all secondary core patches.

This script reads the existing Vec_00/Vec_14 shapefiles (which have UMZ
classifications) and recalculates SL_UC correctly, then updates the
Boundaries_SM shapefiles.
"""

import argparse
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.ops import unary_union

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = PROJECT_ROOT / "replication" / "outputs"


def recalculate_sl_uc(fua_code, vec_dir, year):
    """Recalculate SL_UC for a single FUA."""
    shp_files = list(vec_dir.glob(f"BUILT_{fua_code}_{year}_*.shp"))
    if not shp_files:
        return None

    gdf = gpd.read_file(shp_files[0])

    if 'UMZ' not in gdf.columns:
        return None

    total_area = gdf.geometry.area.sum()
    core2 = gdf[gdf['UMZ'] == 2]

    if len(core2) == 0 or total_area == 0:
        return 0.0

    # Find largest connected component
    core2_union = unary_union(core2.geometry)
    if core2_union.geom_type == 'MultiPolygon':
        largest_component = max(core2_union.geoms, key=lambda g: g.area)
        a_umz2 = largest_component.area
    else:
        a_umz2 = core2_union.area

    return (a_umz2 / total_area) * 100


def fix_boundaries(year, vec_dir, boundaries_shp, sl_uc_col):
    """Fix SL_UC metric for a given year."""
    print(f"\n{'=' * 60}")
    print(f"Fixing {sl_uc_col} in {boundaries_shp.name}")
    print("=" * 60)

    if not boundaries_shp.exists():
        print(f"  File not found: {boundaries_shp}")
        return

    gdf = gpd.read_file(boundaries_shp)
    print(f"Loaded {len(gdf)} FUAs")

    if sl_uc_col not in gdf.columns:
        print(f"  Column {sl_uc_col} not found")
        return

    updated = 0
    for idx, row in gdf.iterrows():
        fua_code = row['fuacode_si']
        old_val = row[sl_uc_col]

        new_val = recalculate_sl_uc(fua_code, vec_dir, year)

        if new_val is not None:
            gdf.loc[idx, sl_uc_col] = new_val
            if pd.notna(old_val) and abs(old_val - new_val) > 0.01:
                updated += 1
                print(f"  {fua_code}: {old_val:.2f}% -> {new_val:.2f}%")

    print(f"\nUpdated {updated} FUAs")
    print(f"Saving to {boundaries_shp}...")
    gdf.to_file(boundaries_shp)

    # Also update CSV if it exists
    csv_path = boundaries_shp.with_suffix('.csv')
    if csv_path.exists():
        # Get numeric columns for CSV
        numeric_cols = gdf.select_dtypes(include=['number']).columns.tolist()
        csv_cols = ['fuacode_si'] + [c for c in numeric_cols if c != 'fuacode_si']
        existing_cols = [c for c in csv_cols if c in gdf.columns]
        gdf[existing_cols].to_csv(csv_path, index=False)
        print(f"Saving to {csv_path.name}...")


def main():
    parser = argparse.ArgumentParser(
        description='Fix SL_UC metric in existing outputs.'
    )
    parser.add_argument(
        '--year', '-y',
        choices=['2000', '2014', 'both'],
        default='both',
        help='Which year to fix (default: both)'
    )
    args = parser.parse_args()

    if args.year in ['2014', 'both']:
        fix_boundaries(
            year='2014',
            vec_dir=OUTPUT_PATH / "Vec_14",
            boundaries_shp=OUTPUT_PATH / "Boundaries_SM_2014.shp",
            sl_uc_col='SL_UC_T2'
        )

    if args.year in ['2000', 'both']:
        fix_boundaries(
            year='2000',
            vec_dir=OUTPUT_PATH / "Vec_00",
            boundaries_shp=OUTPUT_PATH / "Boundaries_SM_2000.shp",
            sl_uc_col='SL_UC_T1'
        )

    print("\nDone!")


if __name__ == "__main__":
    main()
