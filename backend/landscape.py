"""
Landscape metrics module for vegetation patch analysis.
Computes patch count, mean patch size, largest patch index.
"""
import ee
import numpy as np
from typing import Dict, List, Any

from config import SEASON_WINDOWS
from gee_processor import (
    initialize_gee, get_district_geometry, geojson_to_geometry,
    get_season_dates, classify_spectral, classify_dynamic_world,
    dynamic_world_to_landcover, compute_indices, SpectralThresholds,
    simplify_geometry, get_sentinel_collection
)
from schemas import ThresholdsRequest


def get_vegetation_mask(
    geometry: ee.Geometry,
    year: int,
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    cloud_threshold: int = 80
) -> ee.Image:
    """Get binary vegetation mask for a year."""
    initialize_gee()

    start_date, end_date = get_season_dates(year, season)
    simple_geom = simplify_geometry(geometry)

    if classifier == "spectral":
        collection = get_sentinel_collection(
            simple_geom, start_date, end_date, cloud_threshold
        )
        composite = collection.median().clip(simple_geom)
        composite = compute_indices(composite)

        thresh = SpectralThresholds(
            mndwi_water=thresholds.mndwi_water,
            ndvi_water_max=thresholds.ndvi_water_max,
            ndvi_veg_min=thresholds.ndvi_veg_min,
            ndbi_built_min=thresholds.ndbi_built_min,
            ndvi_built_max=thresholds.ndvi_built_max,
        )
        classified = classify_spectral(composite, thresh)
    else:
        dw = classify_dynamic_world(simple_geom, start_date, end_date)
        classified = dynamic_world_to_landcover(dw)

    # Vegetation is class 2
    veg_mask = classified.select("landcover").eq(2).rename("vegetation")
    return veg_mask.clip(simple_geom)


def compute_patch_metrics(
    veg_mask: ee.Image,
    geometry: ee.Geometry,
    scale: int = 20
) -> Dict[str, float]:
    """
    Compute landscape metrics for vegetation patches.
    Uses connected components labeling.
    """
    # Connected components (8-connected)
    # GEE doesn't have built-in connected components, so we approximate
    # using the number of distinct patches via focal operations

    # Alternative approach: use reduceToVectors to get polygons
    # This is more accurate but slower
    vectors = veg_mask.reduceToVectors(
        geometry=geometry,
        scale=scale,
        maxPixels=1e10,
        geometryType="polygon",
        eightConnected=True,
        labelProperty="patch_id",
        crs="EPSG:32643"
    )

    # Get patch areas
    patch_areas = vectors.aggregate_array("area").getInfo()  # in m²

    if not patch_areas:
        return {
            "patch_count": 0,
            "mean_patch_size_km2": 0.0,
            "largest_patch_index": 0.0,
            "total_class_area_km2": 0.0,
        }

    # Convert to km²
    patch_areas_km2 = [a / 1e6 for a in patch_areas]
    total_area = sum(patch_areas_km2)

    patch_count = len(patch_areas_km2)
    mean_patch_size = total_area / patch_count if patch_count > 0 else 0.0
    largest_patch = max(patch_areas_km2) if patch_areas_km2 else 0.0
    largest_patch_index = (largest_patch / total_area * 100) if total_area > 0 else 0.0

    return {
        "patch_count": patch_count,
        "mean_patch_size_km2": mean_patch_size,
        "largest_patch_index": largest_patch_index,
        "total_class_area_km2": total_area,
    }


async def run_landscape_metrics(
    district_id: str,
    geojson: Dict,
    year: int,
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    scale: int = 20,
    cloud_threshold: int = 80
) -> Dict[str, Any]:
    """Run landscape metrics for vegetation in a given year."""
    initialize_gee()

    # Get geometry
    if district_id:
        geometry = get_district_geometry(district_id)
    else:
        geometry = geojson_to_geometry(geojson)

    # Get vegetation mask
    veg_mask = get_vegetation_mask(
        geometry, year, season, classifier, thresholds, cloud_threshold
    )

    # Compute metrics
    metrics = compute_patch_metrics(veg_mask, geometry, scale)

    return {
        "year": year,
        "class": "vegetation",
        **metrics,
    }


async def run_landscape_time_series(
    district_id: str,
    geojson: Dict,
    years: List[int],
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    scale: int = 20,
    cloud_threshold: int = 80
) -> List[Dict[str, Any]]:
    """Run landscape metrics for all years."""
    results = []
    for year in years:
        result = await run_landscape_metrics(
            district_id, geojson, year, season, classifier,
            thresholds, scale, cloud_threshold
        )
        results.append(result)
    return results