"""
Lakes module: detect water bodies per year, rank by area change, flag shrinking lakes.
"""
import ee
from typing import Dict, List, Any, Optional

from gee_processor import (
    initialize_gee, get_district_geometry, geojson_to_geometry,
    get_season_dates, classify_spectral, classify_dynamic_world,
    dynamic_world_to_landcover, compute_indices, SpectralThresholds,
    simplify_geometry, get_sentinel_collection
)
from config import SEASON_WINDOWS
from schemas import ThresholdsRequest


def get_water_mask(
    geometry: ee.Geometry,
    year: int,
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    cloud_threshold: int = 80
) -> ee.Image:
    """Get binary water mask for a year."""
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

    # Water is class 1
    water_mask = classified.select("landcover").eq(1).rename("water")
    return water_mask.clip(simple_geom)


def detect_lakes(
    water_mask: ee.Image,
    geometry: ee.Geometry,
    scale: int = 20,
    min_lake_area_km2: float = 0.01  # 1 hectare minimum
) -> ee.FeatureCollection:
    """Detect individual water bodies (lakes) from water mask."""
    # Convert to vectors (polygons)
    lakes = water_mask.reduceToVectors(
        geometry=geometry,
        scale=scale,
        maxPixels=1e10,
        geometryType="polygon",
        eightConnected=True,
        labelProperty="lake_id",
        crs="EPSG:32643"
    )

    # Add area in km²
    pixel_area = ee.Image.pixelArea().divide(1e6)  # km²

    # We need to compute area per polygon
    # Use reduceRegion on each feature - but that's slow
    # Better: use the area property from reduceToVectors
    # Actually reduceToVectors doesn't add area automatically

    # Alternative: add area as a property using a join
    # Or compute area from the geometry
    def add_area(feature):
        area = feature.geometry().area(1).divide(1e6)  # km²
        return feature.set("area_km2", area)

    lakes_with_area = lakes.map(add_area)

    # Filter by minimum area
    lakes_filtered = lakes_with_area.filter(
        ee.Filter.gte("area_km2", min_lake_area_km2)
    )

    return lakes_filtered


def compute_lake_changes(
    lakes_year1: ee.FeatureCollection,
    lakes_year2: ee.FeatureCollection,
    geometry: ee.Geometry
) -> List[Dict[str, Any]]:
    """Compute area changes between two years' lakes."""
    # This is complex in pure GEE - we'd need to match lakes across years
    # Simplified approach: compute total lake area per year and flag overall change
    # For detailed per-lake tracking, we'd need spatial matching

    # Get stats for each lake collection
    def get_lake_stats(lakes_fc):
        stats = lakes_fc.aggregate_array("area_km2").getInfo()
        return stats

    areas1 = get_lake_stats(lakes_year1)
    areas2 = get_lake_stats(lakes_year2)

    total1 = sum(areas1) if areas1 else 0
    total2 = sum(areas2) if areas2 else 0

    # For per-lake analysis, we return summary stats
    # A full implementation would require spatial join/matching
    return {
        "year1_total_km2": total1,
        "year1_count": len(areas1) if areas1 else 0,
        "year1_areas_km2": areas1,
        "year2_total_km2": total2,
        "year2_count": len(areas2) if areas2 else 0,
        "year2_areas_km2": areas2,
        "total_change_km2": total2 - total1,
        "total_change_pct": ((total2 - total1) / total1 * 100) if total1 > 0 else 0,
    }


async def run_lakes_analysis(
    district_id: str,
    geojson: Dict,
    years: List[int],
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    scale: int = 20,
    cloud_threshold: int = 80,
    shrink_threshold_pct: float = 20.0,
    min_lake_area_km2: float = 0.01,
    lakes_layer_geojson: Optional[Dict] = None  # Optional named lakes layer
) -> Dict[str, Any]:
    """Run complete lakes analysis."""
    initialize_gee()

    # Get geometry
    if district_id:
        geometry = get_district_geometry(district_id)
    else:
        geometry = geojson_to_geometry(geojson)

    # Detect lakes for each year
    yearly_lakes = {}
    yearly_stats = {}

    for year in years:
        water_mask = get_water_mask(
            geometry, year, season, classifier, thresholds, cloud_threshold
        )

        lakes = detect_lakes(water_mask, geometry, scale, min_lake_area_km2)
        yearly_lakes[year] = lakes

        # Get lake stats
        lake_areas = lakes.aggregate_array("area_km2").getInfo()
        lake_geoms = lakes.aggregate_array(".geo").getInfo()  # geometries

        yearly_stats[year] = {
            "year": year,
            "lake_count": len(lake_areas) if lake_areas else 0,
            "total_lake_area_km2": sum(lake_areas) if lake_areas else 0,
            "lakes": [
                {"id": i, "area_km2": area, "geometry": geom}
                for i, (area, geom) in enumerate(zip(lake_areas, lake_geoms))
            ] if lake_areas else [],
        }

    # Compute changes between first and last year
    if len(years) >= 2:
        first_year = years[0]
        last_year = years[-1]

        change = compute_lake_changes(
            yearly_lakes[first_year], yearly_lakes[last_year], geometry
        )

        # Flag lakes that shrank (simplified - using total change)
        # A proper implementation would match individual lakes
        flagged = []
        if change["total_change_pct"] < -shrink_threshold_pct:
            flagged.append({
                "type": "overall",
                "message": f"Total lake area decreased by {abs(change['total_change_pct']):.1f}% "
                           f"({abs(change['total_change_km2']):.2f} km²)"
            })

        # Year-over-year changes
        yoy_changes = []
        for i in range(1, len(years)):
            y1, y2 = years[i - 1], years[i]
            ch = compute_lake_changes(yearly_lakes[y1], yearly_lakes[y2], geometry)
            yoy_changes.append({
                "from_year": y1,
                "to_year": y2,
                **ch,
            })
    else:
        change = {}
        flagged = []
        yoy_changes = []

    return {
        "years": years,
        "yearly_stats": [yearly_stats[y] for y in years],
        "overall_change": change,
        "year_over_year": yoy_changes,
        "flagged_lakes": flagged,
        "shrink_threshold_pct": shrink_threshold_pct,
        "summary": {
            "total_lakes_first_year": yearly_stats[years[0]]["lake_count"] if years else 0,
            "total_lakes_last_year": yearly_stats[years[-1]]["lake_count"] if years else 0,
            "total_area_change_km2": change.get("total_change_km2", 0),
            "total_area_change_pct": change.get("total_change_pct", 0),
        },
    }