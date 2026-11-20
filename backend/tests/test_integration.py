"""
Integration tests for the FastAPI backend.
Tests API endpoints with mocked GEE responses.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return AsyncClient(app=app, base_url="http://test")


@pytest.fixture
def mock_gee():
    """Mock GEE initialization and processing."""
    with patch('main.initialize_gee') as mock_init, \
         patch('main.run_analysis') as mock_analysis, \
         patch('main.get_tile_url') as mock_tiles, \
         patch('main.run_accuracy_assessment') as mock_validate, \
         patch('main.run_trend_analysis') as mock_trend, \
         patch('main.run_transition_analysis') as mock_transitions, \
         patch('main.run_landscape_time_series') as mock_landscape, \
         patch('main.run_urban_growth_analysis') as mock_urban, \
         patch('main.run_environmental_analysis') as mock_env, \
         patch('main.run_lakes_analysis') as mock_lakes, \
         patch('main.run_hotspot_analysis') as mock_hotspots, \
         patch('main.get_cache') as mock_cache:

        mock_init.return_value = None
        mock_cache.return_value.get.return_value = None
        mock_cache.return_value.set.return_value = None

        yield {
            'init': mock_init,
            'analysis': mock_analysis,
            'tiles': mock_tiles,
            'validate': mock_validate,
            'trend': mock_trend,
            'transitions': mock_transitions,
            'landscape': mock_landscape,
            'urban': mock_urban,
            'env': mock_env,
            'lakes': mock_lakes,
            'hotspots': mock_hotspots,
            'cache': mock_cache,
        }


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestRegionsEndpoint:
    """Test /api/regions endpoint."""

    @pytest.mark.asyncio
    async def test_get_regions(self, client):
        response = await client.get("/api/regions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "bengaluru_urban"
        assert data[1]["id"] == "gautam_buddha_nagar"
        assert "bounds" in data[0]
        assert "center" in data[0]


class TestAnalysisEndpoint:
    """Test /api/analysis endpoint."""

    @pytest.mark.asyncio
    async def test_analysis_valid_request(self, client, mock_gee):
        mock_gee['analysis'].return_value = {
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
            "thresholds": {"mndwi_water": 0.10, "ndvi_water_max": 0.15, "ndvi_veg_min": 0.35, "ndbi_built_min": 0.0, "ndvi_built_max": 0.20},
            "scale": 20,
            "baseline_year": 2020,
            "stats": [
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
                    "quality": {"low_image_count": False, "low_coverage": False, "outlier_flag": False, "outlier_details": None, "images_used": 8, "valid_coverage_pct": 85.0},
                    "raw_district_km2": 220.0
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
                    "quality": {"low_image_count": False, "low_coverage": False, "outlier_flag": False, "outlier_details": None, "images_used": 22, "valid_coverage_pct": 90.0},
                    "raw_district_km2": 220.0
                }
            ],
            "recommended_baseline_year": 2020,
            "quality_summary": {"years_with_warnings": 0, "outlier_years": [], "best_quality_year": 2020},
            "run_metadata": {"run_date": "2024-01-15T10:30:00Z", "gee_project": "graphic-tide-513321-m3"}
        }

        response = await client.post("/api/analysis", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
            "thresholds": {"mndwi_water": 0.10, "ndvi_water_max": 0.15, "ndvi_veg_min": 0.35, "ndbi_built_min": 0.0, "ndvi_built_max": 0.20},
            "cloud_threshold": 80,
            "scale": 20
        })

        assert response.status_code == 200
        data = response.json()
        assert data["district_id"] == "bengaluru_urban"
        assert len(data["stats"]) == 2
        assert data["stats"][0]["year"] == 2018
        assert data["stats"][1]["year"] == 2025

    @pytest.mark.asyncio
    async def test_analysis_invalid_year(self, client):
        response = await client.post("/api/analysis", json={
            "district_id": "bengaluru_urban",
            "years": [2026],  # Outside study period
        })
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_analysis_background_mode(self, client, mock_gee):
        response = await client.post("/api/analysis?background=true", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
        })
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


class TestTilesEndpoint:
    """Test /api/tiles endpoint."""

    @pytest.mark.asyncio
    async def test_get_tiles_valid(self, client, mock_gee):
        mock_gee['tiles'].return_value = {
            "tile_url": "https://earthengine.googleapis.com/map/abc123/{z}/{x}/{y}",
            "token": "abc123",
            "bounds": {"west": 77.2, "south": 12.8, "east": 77.8, "north": 13.3},
            "min_zoom": 8,
            "max_zoom": 16,
        }

        response = await client.get("/api/tiles", params={
            "layer": "landcover",
            "year": 2025,
            "district_id": "bengaluru_urban",
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert "tile_url" in data
        assert data["min_zoom"] == 8
        assert data["max_zoom"] == 16

    @pytest.mark.asyncio
    async def test_get_tiles_invalid_year(self, client):
        response = await client.get("/api/tiles", params={
            "layer": "landcover",
            "year": 2026,
            "district_id": "bengaluru_urban",
        })
        assert response.status_code == 400


class TestValidateEndpoint:
    """Test /api/validate endpoint."""

    @pytest.mark.asyncio
    async def test_validate_with_worldcover(self, client, mock_gee):
        mock_gee['validate'].return_value = MagicMock(
            confusion_matrix=[[45, 2, 1, 0], [3, 240, 5, 2], [0, 4, 48, 1], [1, 0, 2, 47]],
            classes=["water", "vegetation", "built_bare", "other"],
            overall_accuracy=0.92,
            balanced_accuracy=0.89,
            producers_accuracy={"water": 0.92, "vegetation": 0.96, "built_bare": 0.86, "other": 0.94},
            users_accuracy={"water": 0.94, "vegetation": 0.94, "built_bare": 0.91, "other": 0.94},
            kappa=0.88,
            sample_size=398,
        )

        response = await client.post("/api/validate", json={
            "district_id": "bengaluru_urban",
            "year": 2020,
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["overall_accuracy"] == 0.92
        assert data["reference_source"] == "WorldCover"

    @pytest.mark.asyncio
    async def test_validate_invalid_year(self, client):
        response = await client.post("/api/validate", json={
            "district_id": "bengaluru_urban",
            "year": 2019,  # WorldCover not available
        })
        # Should not fail but return warning
        assert response.status_code in [200, 400]


class TestTrendEndpoint:
    """Test /api/trend endpoint."""

    @pytest.mark.asyncio
    async def test_trend_valid(self, client, mock_gee):
        mock_gee['analysis'].return_value = {
            "stats": [
                {"year": y, "vegetation_pct": 25 + i * 0.3, "water_pct": 5, "built_bare_pct": 20, "mean_ndvi": 0.3, "mean_mndwi": -0.1, "mean_ndbi": 0.05}
                for i, y in enumerate([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
            ]
        }

        mock_gee['trend'].return_value = {
            "variable": "vegetation",
            "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
            "values": [25.0, 25.3, 25.6, 25.9, 26.2, 26.5, 26.8, 27.1],
            "mann_kendall": {"tau": 0.9, "p_value": 0.001, "s": 28, "var_s": 28.7, "z": 3.5, "significant": True, "trend": "increasing"},
            "sen_slope": {"slope": 0.3, "intercept": -575, "ci_lower": 0.2, "ci_upper": 0.4, "confidence": 0.95},
            "linear_regression": {"slope": 0.3, "intercept": -575, "r_squared": 0.95, "p_value": 0.0001, "ci_lower": 0.25, "ci_upper": 0.35, "significant": True},
            "interpretation": "Vegetation shows significant increasing trend...",
            "warnings": ["WARNING: Only 8 data points..."]
        }

        response = await client.post("/api/trend", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
            "variable": "vegetation",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["mann_kendall"]["significant"] is True
        assert "WARNING" in data["interpretation"]


class TestTransitionsEndpoint:
    """Test /api/transitions endpoint."""

    @pytest.mark.asyncio
    async def test_transitions_valid(self, client, mock_gee):
        mock_gee['transitions'].return_value = {
            "from_year": 2018,
            "to_year": 2025,
            "classes": ["water", "vegetation", "built_bare", "other"],
            "matrix_km2": [[9.5, 0.3, 0.2, 0.1], [0.4, 48.2, 1.2, 0.4], [0.1, 0.8, 38.5, 0.9], [0.0, 0.5, 0.3, 95.2]],
            "matrix_pct": [[4.8, 0.2, 0.1, 0.1], [0.2, 24.1, 0.6, 0.2], [0.0, 0.4, 19.3, 0.5], [0.0, 0.3, 0.2, 47.6]],
            "net_change_km2": {"water": 0.5, "vegetation": 5.2, "built_bare": 9.8, "other": -15.5},
            "total_valid_km2": 200.0
        }

        response = await client.post("/api/transitions", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["from_year"] == 2018
        assert data["to_year"] == 2025


class TestLandscapeEndpoint:
    """Test /api/landscape endpoint."""

    @pytest.mark.asyncio
    async def test_landscape_valid(self, client, mock_gee):
        mock_gee['landscape'].return_value = [
            {"year": 2018, "class": "vegetation", "patch_count": 1250, "mean_patch_size_km2": 0.042, "largest_patch_index": 15.3, "total_class_area_km2": 52.5},
            {"year": 2025, "class": "vegetation", "patch_count": 1100, "mean_patch_size_km2": 0.05, "largest_patch_index": 18.2, "total_class_area_km2": 55.0},
        ]

        response = await client.post("/api/landscape", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["patch_count"] == 1250


class TestUrbanGrowthEndpoint:
    """Test /api/urban-growth endpoint."""

    @pytest.mark.asyncio
    async def test_urban_growth_valid(self, client, mock_gee):
        mock_gee['urban'].return_value = {
            "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
            "yearly_built_area_km2": {"2018": 40.3, "2019": 42.1, "2020": 43.5, "2021": 45.2, "2022": 47.1, "2023": 48.5, "2024": 49.8, "2025": 50.0},
            "growth_rates": [{"year": 2019, "previous_year": 2018, "built_km2": 42.1, "previous_built_km2": 40.3, "absolute_change_km2": 1.8, "growth_rate_pct": 4.5}],
            "expansion_direction": [{"sector": 0, "direction": "N", "angle_center": 11.25, "pixel_count": 1250}],
            "distance_profile_latest": [{"distance_km": 0.5, "built_area_km2": 2.1, "bin_start_km": 0, "bin_end_km": 1}],
            "yearly_distance_profiles": {},
            "center_point": [77.59, 12.97]
        }

        response = await client.post("/api/urban-growth", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert "growth_rates" in data
        assert "expansion_direction" in data


class TestEnvironmentalEndpoint:
    """Test /api/environmental endpoint."""

    @pytest.mark.asyncio
    async def test_environmental_valid(self, client, mock_gee):
        mock_gee['analysis'].return_value = {
            "stats": [{"built_bare_km2": 40 + i} for i in range(8)]
        }
        mock_gee['env'].return_value = {
            "correlations": {"built_vs_lst": 0.65, "built_vs_ntl": 0.72, "built_vs_population": 0.81, "built_vs_rainfall": -0.23},
            "lst_trend": [{"year": 2018, "mean_lst_celsius": 28.5}],
            "ntl_trend": [{"year": 2018, "mean_ntl_radiance": 12.3}],
            "population_trend": [{"year": 2018, "total_population": 12500000}],
            "rainfall_trend": [{"year": 2018, "annual_rainfall_mm": 920}],
        }

        response = await client.post("/api/environmental", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert "correlations" in data


class TestLakesEndpoint:
    """Test /api/lakes endpoint."""

    @pytest.mark.asyncio
    async def test_lakes_valid(self, client, mock_gee):
        mock_gee['lakes'].return_value = {
            "years": [2018, 2025],
            "yearly_stats": [
                {"year": 2018, "lake_count": 45, "total_lake_area_km2": 12.3, "lakes": []},
                {"year": 2025, "lake_count": 42, "total_lake_area_km2": 10.8, "lakes": []},
            ],
            "overall_change": {"year1_total_km2": 12.3, "year2_total_km2": 10.8, "total_change_km2": -1.5, "total_change_pct": -12.2},
            "year_over_year": [],
            "flagged_lakes": [{"type": "overall", "message": "Total lake area decreased by 12.2%"}],
            "summary": {"total_lakes_first_year": 45, "total_lakes_last_year": 42, "total_area_change_km2": -1.5, "total_area_change_pct": -12.2},
        }

        response = await client.post("/api/lakes", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_lakes_first_year"] == 45


class TestHotspotsEndpoint:
    """Test /api/hotspots endpoint."""

    @pytest.mark.asyncio
    async def test_hotspots_valid(self, client, mock_gee):
        mock_gee['hotspots'].return_value = {
            "from_year": 2018,
            "to_year": 2025,
            "cell_size_km": 1.0,
            "top_n": 20,
            "vegetation_loss": [{"cell_id": 123, "col": 5, "row": 12, "veg_loss_km2": 0.85, "geometry": {}}],
            "built_up_gain": [{"cell_id": 456, "col": 8, "row": 3, "built_gain_km2": 1.2, "geometry": {}}],
        }

        response = await client.post("/api/hotspots", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
            "season": {"name": "oct-dec"},
            "classifier": "spectral",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["from_year"] == 2018
        assert data["to_year"] == 2025


class TestReportEndpoint:
    """Test /api/report endpoint."""

    @pytest.mark.asyncio
    async def test_report_not_implemented(self, client):
        response = await client.post("/api/report", json={
            "district_id": "bengaluru_urban",
            "years": [2018, 2025],
        })
        assert response.status_code == 501


class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.mark.asyncio
    async def test_root(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Urban Green and Blue Change Monitor"
        assert "study_period" in data
        assert "districts" in data


class TestErrorHandling:
    """Test error responses."""

    @pytest.mark.asyncio
    async def test_404_job(self, client):
        response = await client.get("/api/jobs/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_district(self, client, mock_gee):
        mock_gee['analysis'].side_effect = ValueError("Unknown district: invalid")
        response = await client.post("/api/analysis", json={
            "district_id": "invalid",
            "years": [2018],
        })
        # Should return 400 or 500 depending on error handling
        assert response.status_code in [400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])