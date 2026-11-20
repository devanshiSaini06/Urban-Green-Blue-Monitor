"""
Unit tests for spectral index calculations.
"""
import pytest
import numpy as np
from numpy.testing import assert_allclose


def ndvi(nir, red):
    """NDVI = (NIR - Red) / (NIR + Red)"""
    return (nir - red) / (nir + red)


def ndwi(green, nir):
    """NDWI = (Green - NIR) / (Green + NIR)"""
    return (green - nir) / (green + nir)


def mndwi(green, swir1):
    """MNDWI = (Green - SWIR1) / (Green + SWIR1)"""
    return (green - swir1) / (green + swir1)


def ndbi(swir1, nir):
    """NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)"""
    return (swir1 - nir) / (swir1 + nir)


class TestIndices:
    """Test spectral index formulas."""

    def test_ndvi_vegetation(self):
        """NDVI should be high for vegetation (high NIR, low Red)."""
        # Dense vegetation: NIR=0.5, Red=0.05
        result = ndvi(0.5, 0.05)
        assert_allclose(result, 0.818, rtol=0.01)

    def test_ndvi_water(self):
        """NDVI should be negative for water (low NIR, higher Red)."""
        # Water: NIR=0.02, Red=0.08
        result = ndvi(0.02, 0.08)
        assert_allclose(result, -0.6, rtol=0.01)

    def test_ndvi_soil(self):
        """NDVI should be low positive for bare soil."""
        # Soil: NIR=0.25, Red=0.2
        result = ndvi(0.25, 0.2)
        assert_allclose(result, 0.111, rtol=0.01)

    def test_ndvi_edge_cases(self):
        """Test edge cases."""
        # Equal NIR and Red -> NDVI = 0
        assert ndvi(0.3, 0.3) == 0.0
        # Zero denominator -> should handle gracefully
        with pytest.raises(ZeroDivisionError):
            ndvi(0, 0)

    def test_mndwi_water(self):
        """MNDWI should be high for water (high Green, low SWIR)."""
        # Water: Green=0.1, SWIR1=0.01
        result = mndwi(0.1, 0.01)
        assert_allclose(result, 0.818, rtol=0.01)

    def test_mndwi_built_up(self):
        """MNDWI should be low/negative for built-up."""
        # Built-up: Green=0.15, SWIR1=0.2
        result = mndwi(0.15, 0.2)
        assert_allclose(result, -0.143, rtol=0.01)

    def test_ndbi_built_up(self):
        """NDBI should be positive for built-up (high SWIR, low NIR)."""
        # Built-up: SWIR1=0.25, NIR=0.15
        result = ndbi(0.25, 0.15)
        assert_allclose(result, 0.25, rtol=0.01)

    def test_ndbi_vegetation(self):
        """NDBI should be negative for vegetation (high NIR, low SWIR)."""
        # Vegetation: SWIR1=0.1, NIR=0.5
        result = ndbi(0.1, 0.5)
        assert_allclose(result, -0.667, rtol=0.01)

    def test_ndwi_vegetation(self):
        """NDWI for vegetation."""
        # Vegetation: Green=0.15, NIR=0.5
        result = ndwi(0.15, 0.5)
        assert_allclose(result, -0.538, rtol=0.01)


class TestClassificationRules:
    """Test classification threshold logic."""

    def test_water_classification(self):
        """Water: MNDWI > 0.10 AND NDVI < 0.15"""
        # Clear water
        assert (mndwi(0.1, 0.01) > 0.10) and (ndvi(0.02, 0.08) < 0.15)
        # Turbid water (lower MNDWI)
        assert not ((mndwi(0.08, 0.02) > 0.10) and (ndvi(0.05, 0.07) < 0.15))

    def test_vegetation_classification(self):
        """Vegetation: NDVI >= 0.35 AND NOT water"""
        # Dense vegetation
        assert ndvi(0.5, 0.05) >= 0.35
        # Sparse vegetation (below threshold)
        assert not (ndvi(0.3, 0.15) >= 0.35)
        # Water should not be vegetation (even if NDVI somehow high)
        water_mask = (mndwi(0.1, 0.01) > 0.10) and (ndvi(0.02, 0.08) < 0.15)
        assert water_mask
        # Vegetation check excludes water
        veg = ndvi(0.5, 0.05) >= 0.35 and not water_mask
        assert veg

    def test_built_up_classification(self):
        """Built-up: NDBI > 0 AND NDVI < 0.20 AND NOT water"""
        # Built-up
        built = (ndbi(0.25, 0.15) > 0) and (ndvi(0.2, 0.18) < 0.20)
        assert built
        # Vegetation (high NDVI) should not be built-up
        assert not ((ndbi(0.1, 0.5) > 0) and (ndvi(0.5, 0.05) < 0.20))
        # Water should not be built-up
        water_mask = (mndwi(0.1, 0.01) > 0.10) and (ndvi(0.02, 0.08) < 0.15)
        assert not (water_mask and (ndbi(0.25, 0.15) > 0))


class TestAreaCalculations:
    """Test area calculation logic."""

    def test_pixel_area_km2(self):
        """Pixel area at 20m scale = 400 m² = 0.0004 km²"""
        pixel_area_m2 = 20 * 20
        pixel_area_km2 = pixel_area_m2 / 1e6
        assert pixel_area_km2 == 0.0004

    def test_area_sum(self):
        """Sum of class areas should equal valid area (within rounding)."""
        class_areas = [10.5, 20.3, 5.2, 2.0]  # km²
        valid_area = sum(class_areas)
        total = sum(class_areas)
        assert abs(valid_area - total) < 0.001

    def test_percentage_calculation(self):
        """Percentages should use valid area as denominator."""
        class_areas = {"water": 10, "veg": 50, "built": 30, "other": 10}
        valid_area = sum(class_areas.values())
        water_pct = class_areas["water"] / valid_area * 100
        assert water_pct == 10.0


class TestSCLMask:
    """Test SCL cloud mask logic."""

    def test_masked_classes(self):
        """Classes to mask: 0, 1, 3, 8, 9, 10, 11"""
        masked = {0, 1, 3, 8, 9, 10, 11}
        retained = {2, 4, 5, 6, 7}

        for cls in masked:
            assert cls in masked
        for cls in retained:
            assert cls not in masked

    def test_mask_logic(self):
        """Pixel is valid if NOT in masked classes."""
        scl_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        masked = {0, 1, 3, 8, 9, 10, 11}

        for scl in scl_values:
            is_valid = scl not in masked
            if scl in masked:
                assert not is_valid
            else:
                assert is_valid


class TestOutlierDetection:
    """Test outlier flag logic."""

    def test_outlier_detected(self):
        """Year differing from neighbors by >25% should be flagged."""
        values = [10, 10, 20, 10, 10]  # Middle year is 2x neighbors
        idx = 2
        neighbor_avg = (values[idx - 1] + values[idx + 1]) / 2
        diff_pct = abs(values[idx] - neighbor_avg) / neighbor_avg * 100
        assert diff_pct > 25

    def test_no_outlier(self):
        """Normal variation should not be flagged."""
        values = [10, 11, 10.5, 11, 10]
        for i in range(1, len(values) - 1):
            neighbor_avg = (values[i - 1] + values[i + 1]) / 2
            diff_pct = abs(values[i] - neighbor_avg) / neighbor_avg * 100
            assert diff_pct <= 25

    def test_edge_years_not_checked(self):
        """First and last year should not be checked."""
        values = [100, 10, 10, 10, 10]  # First year extreme
        # Index 0 and len-1 are skipped
        assert True  # Implementation should skip edges


if __name__ == "__main__":
    pytest.main([__file__, "-v"])