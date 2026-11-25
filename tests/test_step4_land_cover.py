"""
Unit tests for step4_land_cover.py

Tests the helper functions for CCI Land Cover processing.
"""

import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import box

from step4_land_cover import (
    CCI_LC_BANDS,
    CCI_LC_SINGLE_YEAR,
    RECLASS_CCI,
    calc_lc_density,
    detect_cci_format,
    reclassify_cci,
)
from utils import (
    BOUNDARIES_PATH,
    DATA_PATH,
    PROJECT_ROOT,
    UTM_ZONES_PATH,
)


class TestReclassifyCCI:
    """Tests for the reclassify_cci function."""

    def test_agriculture_class(self):
        """Test that agriculture values (10-30) map to class 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.tif"
            output_path = Path(tmpdir) / "output.tif"

            # Create test raster with agriculture values
            data = np.array([[10, 20, 30], [15, 25, 11]], dtype=np.uint8)

            with rasterio.open(
                input_path, 'w',
                driver='GTiff',
                height=2, width=3,
                count=1,
                dtype=np.uint8,
                crs='EPSG:4326',
                transform=rasterio.transform.from_bounds(0, 0, 3, 2, 3, 2)
            ) as dst:
                dst.write(data, 1)

            reclassify_cci(input_path, output_path)

            with rasterio.open(output_path) as src:
                result = src.read(1)

            # All values should be reclassified to 1 (Agriculture)
            assert np.all(result == 1), f"Expected all 1s, got {result}"

    def test_forest_class(self):
        """Test that forest values (40-100, 160-180) map to class 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.tif"
            output_path = Path(tmpdir) / "output.tif"

            # Create test raster with forest values
            data = np.array([[40, 70, 100], [160, 170, 180]], dtype=np.uint8)

            with rasterio.open(
                input_path, 'w',
                driver='GTiff',
                height=2, width=3,
                count=1,
                dtype=np.uint8,
                crs='EPSG:4326',
                transform=rasterio.transform.from_bounds(0, 0, 3, 2, 3, 2)
            ) as dst:
                dst.write(data, 1)

            reclassify_cci(input_path, output_path)

            with rasterio.open(output_path) as src:
                result = src.read(1)

            # All values should be reclassified to 2 (Forest)
            assert np.all(result == 2), f"Expected all 2s, got {result}"

    def test_urban_class(self):
        """Test that urban value (190) maps to class 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.tif"
            output_path = Path(tmpdir) / "output.tif"

            data = np.array([[190, 190], [190, 190]], dtype=np.uint8)

            with rasterio.open(
                input_path, 'w',
                driver='GTiff',
                height=2, width=2,
                count=1,
                dtype=np.uint8,
                crs='EPSG:4326',
                transform=rasterio.transform.from_bounds(0, 0, 2, 2, 2, 2)
            ) as dst:
                dst.write(data, 1)

            reclassify_cci(input_path, output_path)

            with rasterio.open(output_path) as src:
                result = src.read(1)

            # All values should be reclassified to 4 (Urban)
            assert np.all(result == 4), f"Expected all 4s, got {result}"

    def test_mixed_classes(self):
        """Test reclassification with mixed land cover values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.tif"
            output_path = Path(tmpdir) / "output.tif"

            # Mix of: Agriculture(20), Forest(50), Urban(190), Water(210)
            data = np.array([[20, 50], [190, 210]], dtype=np.uint8)
            expected = np.array([[1, 2], [4, 6]], dtype=np.uint8)

            with rasterio.open(
                input_path, 'w',
                driver='GTiff',
                height=2, width=2,
                count=1,
                dtype=np.uint8,
                crs='EPSG:4326',
                transform=rasterio.transform.from_bounds(0, 0, 2, 2, 2, 2)
            ) as dst:
                dst.write(data, 1)

            reclassify_cci(input_path, output_path)

            with rasterio.open(output_path) as src:
                result = src.read(1)

            np.testing.assert_array_equal(result, expected)

    def test_nodata_handling(self):
        """Test that zero values remain zero (nodata)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.tif"
            output_path = Path(tmpdir) / "output.tif"

            data = np.array([[0, 20], [190, 0]], dtype=np.uint8)
            expected = np.array([[0, 1], [4, 0]], dtype=np.uint8)

            with rasterio.open(
                input_path, 'w',
                driver='GTiff',
                height=2, width=2,
                count=1,
                dtype=np.uint8,
                crs='EPSG:4326',
                transform=rasterio.transform.from_bounds(0, 0, 2, 2, 2, 2)
            ) as dst:
                dst.write(data, 1)

            reclassify_cci(input_path, output_path)

            with rasterio.open(output_path) as src:
                result = src.read(1)

            np.testing.assert_array_equal(result, expected)


class TestCalcLcDensity:
    """Tests for the calc_lc_density function."""

    def test_empty_geodataframe(self):
        """Test density calculation with empty GeoDataFrame."""
        gdf = gpd.GeoDataFrame(columns=['DN', 'geometry'], crs='EPSG:3857')
        result = calc_lc_density(gdf, 1, 100.0)
        assert result == 0.0

    def test_zero_total_area(self):
        """Test density calculation with zero total area."""
        gdf = gpd.GeoDataFrame(
            {'DN': [1], 'geometry': [box(0, 0, 1000, 1000)]},
            crs='EPSG:3857'
        )
        result = calc_lc_density(gdf, 1, 0.0)
        assert result == 0.0

    def test_class_not_present(self):
        """Test density when requested class is not present."""
        gdf = gpd.GeoDataFrame(
            {'DN': [1, 2], 'geometry': [box(0, 0, 1000, 1000), box(1000, 0, 2000, 1000)]},
            crs='EPSG:3857'
        )
        result = calc_lc_density(gdf, 3, 10.0)
        assert result == 0.0

    def test_single_class_coverage(self):
        """Test density with single class covering known area."""
        # Create a 1km x 1km box (1 km^2)
        gdf = gpd.GeoDataFrame(
            {'DN': [1], 'geometry': [box(0, 0, 1000, 1000)]},
            crs='EPSG:3857'
        )
        # Total area is 10 km^2, class area is 1 km^2
        result = calc_lc_density(gdf, 1, 10.0)
        assert abs(result - 10.0) < 0.01  # 10% of total area

    def test_multiple_patches_same_class(self):
        """Test density with multiple patches of the same class."""
        # Two 1km x 1km boxes (2 km^2 total)
        gdf = gpd.GeoDataFrame(
            {'DN': [1, 1], 'geometry': [box(0, 0, 1000, 1000), box(2000, 0, 3000, 1000)]},
            crs='EPSG:3857'
        )
        result = calc_lc_density(gdf, 1, 10.0)
        assert abs(result - 20.0) < 0.01  # 20% of total area


class TestDataPaths:
    """Test that required data paths exist."""

    def test_project_root_exists(self):
        """Test that project root exists."""
        assert PROJECT_ROOT.exists(), f"Project root not found: {PROJECT_ROOT}"

    def test_data_path_exists(self):
        """Test that data path exists."""
        assert DATA_PATH.exists(), f"Data path not found: {DATA_PATH}"

    def test_boundaries_exist(self):
        """Test that boundaries shapefiles exist."""
        boundaries_4326 = BOUNDARIES_PATH / "Boundaries_4326.shp"
        boundaries_3857 = BOUNDARIES_PATH / "Boundaries_3857.shp"
        assert boundaries_4326.exists(), f"Boundaries 4326 not found: {boundaries_4326}"
        assert boundaries_3857.exists(), f"Boundaries 3857 not found: {boundaries_3857}"

    def test_utm_zones_exist(self):
        """Test that UTM zones shapefile exists."""
        utm_zones = UTM_ZONES_PATH / "UTM_Zone_EPSG_4326.shp"
        assert utm_zones.exists(), f"UTM zones not found: {utm_zones}"


class TestReclassMapping:
    """Test that the reclassification mapping is correct."""

    def test_all_classes_defined(self):
        """Test that all 7 classes are defined in the mapping."""
        all_values = set(RECLASS_CCI.values())

        expected_classes = {1, 2, 3, 4, 5, 6, 7}
        assert expected_classes == all_values, f"Missing classes: {expected_classes - all_values}"

    def test_class_ranges(self):
        """Test specific class ranges."""
        # Agriculture: 10-30 -> 1
        assert RECLASS_CCI[(10, 30)] == 1
        # Forest: 40-100 -> 2
        assert RECLASS_CCI[(40, 100)] == 2
        # Urban: 190 -> 4
        assert RECLASS_CCI[190] == 4
        # Water: 210 -> 6
        assert RECLASS_CCI[210] == 6


class TestCCIFormatDetection:
    """Tests for CCI format auto-detection."""

    def test_detect_format_returns_valid_type(self):
        """Test that detect_cci_format returns a valid format type."""
        format_type, data_source = detect_cci_format()

        # Should return either a valid format or None
        assert format_type in ('multitemporal', 'single_year', None)

    def test_multitemporal_config(self):
        """Test multi-temporal configuration is correct."""
        assert CCI_LC_BANDS[2000] == 9
        assert CCI_LC_BANDS[2014] == 23

    def test_single_year_config(self):
        """Test single-year file configuration."""
        assert 2000 in CCI_LC_SINGLE_YEAR
        assert 2014 in CCI_LC_SINGLE_YEAR


class TestIntegration:
    """Integration tests for the full processing pipeline."""

    def test_process_single_fua(self):
        """Test processing a single FUA end-to-end."""
        import step4_land_cover as s4

        # Load boundaries
        boundaries_4326 = gpd.read_file(s4.BOUNDARIES_4326_PATH)
        utm_zones = gpd.read_file(s4.UTM_ZONES_PATH)

        # Use first Australian FUA for testing
        test_fua = 'AUS05'
        fua_4326 = boundaries_4326[boundaries_4326['fuacode_si'] == test_fua].copy()

        if len(fua_4326) == 0:
            pytest.skip(f"Test FUA {test_fua} not found in boundaries")

        # Detect CCI format
        cci_format, cci_data = s4.detect_cci_format()
        if cci_format is None:
            pytest.skip("No CCI data available")

        # Initialize results
        results_gdf = s4.initialize_output_shapefile()

        # Process FUA with detected format
        metrics = s4.process_fua(test_fua, fua_4326, utm_zones, results_gdf,
                                  cci_format=cci_format, cci_data=cci_data)

        # Verify we got metrics
        assert metrics['fuacode_si'] == test_fua

        # Check that at least some density values were calculated
        density_values = [metrics[f'D_LC{i}_T1'] for i in range(1, 8)]
        valid_densities = [v for v in density_values if not np.isnan(v)]
        assert len(valid_densities) > 0, "No density values were calculated"

        # Check densities sum approximately to 100%
        total_t1 = sum(metrics[f'D_LC{i}_T1'] for i in range(1, 8) if not np.isnan(metrics[f'D_LC{i}_T1']))
        assert 95.0 < total_t1 < 105.0, f"Densities should sum to ~100%, got {total_t1}%"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
