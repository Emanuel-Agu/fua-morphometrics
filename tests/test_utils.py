"""Unit tests for spatial statistics, metrics, and geometry helpers in scripts/utils.py."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, box

from utils import (
    DATA_PATH,
    OUTPUT_PATH,
    PROJECT_ROOT,
    calc_compactness,
    calc_dispersion_index,
    calc_elongation_ratio,
    calc_landscape_expansion_index,
    classify_growth_type,
    create_fishnet_points,
    get_mbr_dimensions,
    get_utm_epsg,
    identify_second_urban_core,
    identify_urban_core,
    standard_distance,
)


def test_project_paths_resolve_to_repo_root():
    assert PROJECT_ROOT.is_dir()
    assert (PROJECT_ROOT / "pyproject.toml").exists()
    assert DATA_PATH == PROJECT_ROOT / "data"
    assert OUTPUT_PATH == PROJECT_ROOT / "outputs"


def test_standard_distance_weighted_and_unweighted():
    # Two squares centred at (0, 0) and (200, 0) -> unweighted SD = 100
    gdf = gpd.GeoDataFrame(
        {"Area": [100.0, 100.0]},
        geometry=[box(-5, -5, 5, 5), box(195, -5, 205, 5)],
        crs="EPSG:32630",
    )
    assert standard_distance(gdf) == pytest.approx(100.0)
    assert standard_distance(gdf, weight_col="Area") == pytest.approx(100.0)
    assert standard_distance(gdf.iloc[0:0]) == 0.0


def test_create_fishnet_points():
    area = box(0, 0, 4000, 4000)
    pts = create_fishnet_points(area.bounds, cell_size=2000, clip_geometry=area)
    assert len(pts) == 4


def test_get_mbr_dimensions():
    width, length = get_mbr_dimensions(box(0, 0, 100, 300))
    assert width == pytest.approx(100.0)
    assert length == pytest.approx(300.0)
    assert get_mbr_dimensions(Point(0, 0)) == (0.0, 0.0)


def test_calc_compactness_circle_and_square():
    # Circle: C = 100; Square: C = 100 * sqrt(pi) / 2
    r = 100.0
    assert calc_compactness(np.pi * r**2, 2 * np.pi * r) == pytest.approx(100.0)
    assert calc_compactness(100.0, 40.0) == pytest.approx(100.0 * np.sqrt(np.pi) / 2.0)
    assert calc_compactness(100.0, 0.0) == 0.0


def test_calc_dispersion_index():
    # Single patch covering all pixels -> DI = 0
    assert calc_dispersion_index(1, 100, 100.0, 100.0) == pytest.approx(0.0)
    assert calc_dispersion_index(1, 1, 1.0, 1.0) == 0.0


def test_calc_elongation_ratio():
    # Circle of radius 50: area=pi*50^2, MBR length=100 -> ER = 1.0
    assert calc_elongation_ratio(np.pi * 50.0**2, 100.0) == pytest.approx(1.0)
    assert calc_elongation_ratio(100.0, 0.0) == 0.0


def test_identify_urban_cores():
    gdf = gpd.GeoDataFrame(
        {"Area": [10_000.0, 4_000.0, 2_500.0]},
        geometry=[
            box(0, 0, 100, 100),         # largest patch
            box(250, 0, 350, 40),        # 150 m from patch 0 -> joins core 1
            box(2000, 0, 2050, 50),      # far away -> becomes core 2
        ],
        crs="EPSG:32630",
    )
    core1 = identify_urban_core(gdf, area_col="Area", distance=200, iterations=2)
    assert set(core1.index) == {0, 1}

    core2 = identify_second_urban_core(gdf, core1, area_col="Area", distance=200, iterations=2)
    assert set(core2.index) == {2}


def test_get_utm_epsg():
    assert get_utm_epsg(-0.376, 39.469) == 32630  # Valencia (30N)
    assert get_utm_epsg(-58.381, -34.603) == 32721  # Buenos Aires (21S)


def test_lei_and_growth_classification():
    existing = box(0, 0, 100, 100)
    outlying_patch = box(500, 500, 600, 600)
    edge_patch = box(100, 0, 200, 100)  # shares 100 of 400 perimeter -> LEI = 0.25

    assert calc_landscape_expansion_index(outlying_patch, existing) == pytest.approx(0.0)
    assert calc_landscape_expansion_index(edge_patch, existing) == pytest.approx(0.25)

    assert classify_growth_type(0.0) == "Outlying"
    assert classify_growth_type(0.25) == "Edge-Expansive"
    assert classify_growth_type(0.75) == "Infilling"
