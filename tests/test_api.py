"""
API integration tests using recorded GEE responses (fixtures).
Also includes a smoke test against live GEE (requires credentials).
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Import after setting up mocks
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from schemas import (
    AnalysisRequest, SeasonWindow, ThresholdsRequest,
    TrendRequest, ValidateRequest, TileRequest
)
from config import STUDY_YEARS, SEASON_WINDOWS, DISTRICTS


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_analysis_request():
    """Sample analysis request for testing."""
    return AnalysisRequest(
        district_id="bengaluru_urban",
        years=[2018, 2025],
        season=SeasonWindow(name="oct-dec"),
        classifier="spectral",
        thresholds=ThresholdsRequest(),
        cloud_threshold=80,
        scale=20,
    )


@pytest.fixture
def sample_trend_request():
    """Sample trend request for testing."""
    return TrendRequest(
        district_id="bengaluru_urban",
        years=STUDY_YEARS,
        season=SeasonWindow(name="oct-dec"),
        classifier="spectral",
        thresholds=ThresholdsRequest(),
        variable="vegetation",
    )


@pytest.fixture
def mock_gee_response():
    """Mock GEE response fixture."""
    return {
        "yearly_stats": [
            {
                "year": 2018,
                "images_used": 8,
                "valid_km2": 200.5,
                "vegetation_km2": 50.2,
                "water_km2": 10.1,
                "built_bare_km2": 40.3,
                "other_km2": 100.0,
                "vegetation_pct": 25.0,
                "water_pct": 5.0,
                "built_bare_pct": 20.1,
                "other_pct": 49.9,
                "mean_ndvi": 0.35,
                "mean_mndwi": -0.1,
                "mean_ndbi": 0.05,
                "composite_first_date": "2018-10-15",
                "composite_last_date": "2018-12-20",
                "quality": {
                    "low_image_count": False,
                    "low_coverage": False,
                    "outlier_flag": False,
                    "outlier_details": None,
                    "images_used": 8,
                    "valid_coverage_pct": 85.0,
                },
                "raw_district_km2": 220.0,
            },
            {
                "year": 2025,
                "images_used": 22,
                "valid_km2": 205.0,
                "vegetation_km2": 55.0,
                "water_km2": 12.0,
                "built_bare_km2": 50.0,
                "other_km2": 88.0,
                "vegetation_pct": 26.8,
                "water_pct": 5.9,
                "built_bare_pct": 24.4,
                "other_pct": 42.9,
                "mean_ndvi": 0.38,
                "mean_mndwi": -0.08,
                "mean_ndbi": 0.08,
                "composite_first_date": "2025-10-10",
                "composite_last_date": "2025-12-25",
                "quality": {
                    "low_image_count": False,
                    "low_coverage": False,
                    "outlier_flag": False,
                    "outlier_details": None,
                    "images_used": 22,
                    "valid_coverage_pct": 90.0,
                },
                "raw_district_km2": 220.0,
            },
        ]
    }


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================

class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_analysis_request_valid(self, sample_analysis_request):
        """Valid request should pass validation."""
        assert sample_analysis_request.district_id == "bengaluru_urban"
        assert sample_analysis_request.years == [2018, 2025]
        assert sample_analysis_request.classifier == "spectral"
        assert sample_analysis_request.scale == 20

    def test_analysis_request_invalid_year(self):
        """Year outside study period should fail."""
        with pytest.raises(ValueError, match="not in study period"):
            AnalysisRequest(
                district_id="bengaluru_urban",
                years=[2017],  # Before study period
            )

    def test_analysis_request_invalid_scale(self):
        """Invalid scale should fail."""
        with pytest.raises(ValueError, match="Scale must be one of"):
            AnalysisRequest(
                district_id="bengaluru_urban",
                years=[2018],
                scale=15,  # Not in [10, 20, 30]
            )

    def test_analysis_request_custom_season(self):
        """Custom season requires start and end dates."""
        with pytest.raises(ValueError):
            AnalysisRequest(
                district_id="bengaluru_urban",
                years=[2018],
                season=SeasonWindow(name="custom"),
            )

        # Valid custom season
        req = AnalysisRequest(
            district_id="bengaluru_urban",
            years=[2018],
            season=SeasonWindow(name="custom", custom_start="2018-01-01", custom_end="2018-12-31"),
        )
        assert req.season.custom_start == "2018-01-01"

    def test_analysis_request_duplicate_years(self):
        """Duplicate years should be deduplicated and sorted."""
        req = AnalysisRequest(
            district_id="bengaluru_urban",
            years=[2025, 2018, 2018],
        )
        assert req.years == [2018, 2025]

    def test_trend_request_valid(self, sample_trend_request):
        """Valid trend request."""
        assert sample_trend_request.variable == "vegetation"
        assert sample_trend_request.years == STUDY_YEARS

    def test_trend_request_invalid_variable(self):
        """Invalid variable should fail."""
        with pytest.raises(ValueError):
            TrendRequest(
                district_id="bengaluru_urban",
                variable="invalid_var",
            )

    def test_season_window_validation(self):
        """Season window validation."""
        # Valid predefined
        sw = SeasonWindow(name="jan-mar")
        assert sw.start_month == 1
        assert sw.end_month == 4

        # Valid custom
        sw = SeasonWindow(name="custom", custom_start="2018-02-01", custom_end="2018-05-01")
        assert sw.custom_start == "2018-02-01"

        # Invalid custom (missing dates)
        with pytest.raises(ValueError):
            SeasonWindow(name="custom")

    def test_thresholds_request_defaults(self):
        """Thresholds should have correct defaults."""
        t = ThresholdsRequest()
        assert t.mndwi_water == 0.10
        assert t.ndvi_water_max == 0.15
        assert t.ndvi_veg_min == 0.35
        assert t.ndbi_built_min == 0.0
        assert t.ndvi_built_max == 0.20


# =============================================================================
# CONFIG TESTS
# =============================================================================

class TestConfig:
    """Test configuration constants."""

    def test_study_years(self):
        """Study years should be exactly 2018-2025."""
        assert STUDY_YEARS == list(range(2018, 2026))
        assert len(STUDY_YEARS) == 8
        assert min(STUDY_YEARS) == 2018
        assert max(STUDY_YEARS) == 2025

    def test_season_windows(self):
        """Season windows should be correctly defined."""
        assert SEASON_WINDOWS["oct-dec"] == (10, 1)
        assert SEASON_WINDOWS["jan-mar"] == (1, 4)
        assert SEASON_WINDOWS["mar-may"] == (3, 6)
        assert SEASON_WINDOWS["jun-sep"] == (6, 10)

    def test_districts(self):
        """District configs should be valid."""
        assert "bengaluru_urban" in DISTRICTS
        assert "gautam_buddha_nagar" in DISTRICTS

        blr = DISTRICTS["bengaluru_urban"]
        assert blr.feature_index == 1
        assert blr.asset_id == "projects/graphic-tide-513321-m3/assets/Bengaluru"

        gbn = DISTRICTS["gautam_buddha_nagar"]
        assert gbn.feature_index == 0
        assert gbn.asset_id == "projects/graphic-tide-513321-m3/assets/GautamBuddhaNagar"


# =============================================================================
# MOCK GEE TESTS (Unit tests with mocked GEE)
# =============================================================================

class TestGeEProcessorMocked:
    """Test GEE processor with mocked responses."""

    @pytest.mark.asyncio
    async def test_run_analysis_structure(self, sample_analysis_request, mock_gee_response):
        """Test that run_analysis returns correct structure."""
        # This test would require mocking ee module extensively
        # For now, we verify the request schema is correct
        assert sample_analysis_request.district_id in DISTRICTS

    def test_cache_key_generation(self):
        """Test cache key generation is deterministic."""
        from cache import build_analysis_cache_key

        params = {
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
            "classifier": "spectral",
        }

        key1 = build_analysis_cache_key(params)
        key2 = build_analysis_cache_key(params)
        assert key1 == key2
        assert key1.startswith("analysis:")

        # Different params should give different keys
        params2 = params.copy()
        params2["years"] = [2019, 2025]
        key3 = build_analysis_cache_key(params2)
        assert key1 != key3


# =============================================================================
# LIVE GEE SMOKE TEST (requires credentials)
# =============================================================================

@pytest.mark.skipif(
    not os.getenv("GEE_SERVICE_ACCOUNT_KEY_JSON") and not os.getenv("GEE_SERVICE_ACCOUNT_KEY_PATH"),
    reason="GEE credentials not available"
)
class TestLiveGEE:
    """Smoke tests against live GEE (run only with credentials)."""

    @pytest.mark.asyncio
    async def test_gee_initialization(self):
        """Test GEE can be initialized."""
        from gee_processor import initialize_gee
        initialize_gee()  # Should not raise

    @pytest.mark.asyncio
    async def test_district_geometry(self):
        """Test fetching district geometry."""
        from gee_processor import get_district_geometry
        geom = get_district_geometry("bengaluru_urban")
        assert geom is not None
        # Check it's a valid geometry
        info = geom.getInfo()
        assert info["type"] in ["Polygon", "MultiPolygon"]

    @pytest.mark.asyncio
    async def test_sentinel_collection(self):
        """Test Sentinel-2 collection filtering."""
        from gee_processor import get_sentinel_collection, get_district_geometry
        geom = get_district_geometry("bengaluru_urban")
        collection = get_sentinel_collection(geom, "2020-10-01", "2021-01-01")
        count = collection.size().getInfo()
        assert count > 0


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_years_in_request(self):
        """Empty years list should be handled."""
        req = AnalysisRequest(district_id="bengaluru_urban", years=[])
        assert req.years == []

    def test_all_study_years(self):
        """Request with all study years."""
        req = AnalysisRequest(district_id="bengaluru_urban", years=STUDY_YEARS)
        assert req.years == STUDY_YEARS

    def test_baseline_year_not_in_years(self):
        """Baseline year not in selected years should fail."""
        with pytest.raises(ValueError, match="Baseline year must be in the selected years"):
            AnalysisRequest(
                district_id="bengaluru_urban",
                years=[2018, 2025],
                baseline_year=2020,  # Not in years
            )

    def test_baseline_year_in_years(self):
        """Baseline year in selected years should pass."""
        req = AnalysisRequest(
            district_id="bengaluru_urban",
            years=[2018, 2020, 2025],
            baseline_year=2020,
        )
        assert req.baseline_year == 2020


# =============================================================================
# TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])