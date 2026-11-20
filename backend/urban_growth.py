"""
Urban growth indicators module.
Computes built-up growth rate, expansion direction (rose diagram), distance-from-centre profile.
"""
import ee
import numpy as np
import math
from typing import Dict, List, Any, Tuple

from config import SEASON_WINDOWS
from gee_processor import (
    initialize_gee, get_district_geometry, geojson_to_geometry,
    get_season_dates, classify_spectral, classify_dynamic_world,
    dynamic_world_to_landcover, compute_indices, SpectralThresholds,
    simplify_geometry, get_sentinel_collection
)
from schemas import ThresholdsRequest


def get_built_mask(
    geometry: ee.Geometry,
    year: int,
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    cloud_threshold: int = 80
) -> ee.Image:
    """Get binary built-up/bare mask for a year."""
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

    # Built/bare is class 3
    built_mask = classified.select("landcover").eq(3).rename("built")
    return built_mask.clip(simple_geom)


def compute_growth_rates(
    built_areas_km2: List[float],
    years: List[int]
) -> List[Dict[str, Any]]:
    """Compute year-over-year growth rates."""
    results = []
    for i in range(1, len(built_areas_km2)):
        prev = built_areas_km2[i - 1]
        curr = built_areas_km2[i]
        if prev > 0:
            growth_rate = (curr - prev) / prev * 100
            absolute_change = curr - prev
        else:
            growth_rate = 0.0
            absolute_change = curr

        results.append({
            "year": years[i],
            "previous_year": years[i - 1],
            "built_km2": curr,
            "previous_built_km2": prev,
            "absolute_change_km2": absolute_change,
            "growth_rate_pct": growth_rate,
        })
    return results


def compute_expansion_direction(
    built_mask: ee.Image,
    geometry: ee.Geometry,
    scale: int = 20,
    center_point: ee.Geometry = None
) -> List[Dict[str, Any]]:
    """
    Compute built-up expansion direction (rose diagram).
    Returns area by compass sector.
    """
    # Get centroid if not provided
    if center_point is None:
        center_point = geometry.centroid()

    # Get coordinates
    center_coords = center_point.coordinates().getInfo()
    cx, cy = center_coords[0], center_coords[1]

    # Create distance and angle bands
    # We'll sample points and compute angles
    # Create a grid of points
    pixel_lon = ee.Image.pixelLonLat().select("longitude")
    pixel_lat = ee.Image.pixelLonLat().select("latitude")

    # Compute angle from center (in degrees, 0=North, clockwise)
    dx = pixel_lon.subtract(cx)
    dy = pixel_lat.subtract(cy)

    # atan2(dx, dy) gives angle from north
    angle = dx.atan2(dy).multiply(180 / math.pi).add(180)  # 0-360

    # Bin into 16 sectors (22.5 degrees each)
    sector = angle.divide(22.5).floor().rename("sector")

    # Add sector to built mask
    built_with_sector = built_mask.addBands(sector)

    # Reduce by sector
    stats = built_with_sector.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName="sector"),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        crs="EPSG:32643"
    )

    groups = stats.get("groups").getInfo()

    # Sector labels
    sector_labels = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]

    results = []
    for group in groups:
        sector_idx = int(group["sector"])
        if 0 <= sector_idx < 16:
            area = float(group["sum"])  # This is pixel count, need to convert to area
            results.append({
                "sector": sector_idx,
                "direction": sector_labels[sector_idx],
                "angle_center": sector_idx * 22.5 + 11.25,
                "pixel_count": area,
            })

    return results


def compute_distance_profile(
    built_mask: ee.Image,
    geometry: ee.Geometry,
    center_point: ee.Geometry,
    scale: int = 20,
    max_distance_km: float = 30.0,
    num_bins: int = 30
) -> List[Dict[str, Any]]:
    """
    Compute built-up area as function of distance from center.
    """
    # Get center coordinates
    center_coords = center_point.coordinates().getInfo()
    cx, cy = center_coords[0], center_coords[1]

    # Create distance image (in km)
    pixel_lon = ee.Image.pixelLonLat().select("longitude")
    pixel_lat = ee.Image.pixelLonLat().select("latitude")

    # Haversine distance approximation (good enough for 30km)
    # 1 degree lat ~= 111 km, 1 degree lon ~= 111 * cos(lat) km
    lat_rad = cy * math.pi / 180
    km_per_deg_lon = 111.32 * math.cos(lat_rad)
    km_per_deg_lat = 111.32

    dx_km = pixel_lon.subtract(cx).multiply(km_per_deg_lon)
    dy_km = pixel_lat.subtract(cy).multiply(km_per_deg_lat)

    distance = dx_km.pow(2).add(dy_km.pow(2)).sqrt().rename("distance_km")

    # Bin distance
    bin_width = max_distance_km / num_bins
    distance_bin = distance.divide(bin_width).floor().rename("dist_bin")

    # Combine with built mask
    built_with_dist = built_mask.addBands(distance_bin)

    # Reduce by distance bin
    stats = built_with_dist.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName="dist_bin"),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        crs="EPSG:32643"
    )

    groups = stats.get("groups").getInfo()

    results = []
    for group in groups:
        bin_idx = int(group["dist_bin"])
        if 0 <= bin_idx < num_bins:
            pixel_count = float(group["sum"])
            # Convert to area (approximate)
            pixel_area_km2 = (scale * scale) / 1e6
            area_km2 = pixel_count * pixel_area_km2

            dist_center = (bin_idx + 0.5) * bin_width
            results.append({
                "distance_km": dist_center,
                "bin_start_km": bin_idx * bin_width,
                "bin_end_km": (bin_idx + 1) * bin_width,
                "built_area_km2": area_km2,
                "pixel_count": pixel_count,
            })

    return results


async def run_urban_growth_analysis(
    district_id: str,
    geojson: Dict,
    years: List[int],
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    scale: int = 20,
    cloud_threshold: int = 80
) -> Dict[str, Any]:
    """Run complete urban growth analysis."""
    initialize_gee()

    # Get geometry
    if district_id:
        geometry = get_district_geometry(district_id)
    else:
        geometry = geojson_to_geometry(geojson)

    # Get center point
    center_point = geometry.centroid()

    # Get built-up masks for all years
    built_masks = {}
    built_areas = []

    for year in years:
        built_mask = get_built_mask(
            geometry, year, season, classifier, thresholds, cloud_threshold
        )
        built_masks[year] = built_mask

        # Compute area
        pixel_area = ee.Image.pixelArea().divide(1e6)  # km²
        area = built_mask.multiply(pixel_area).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
            crs="EPSG:32643"
        ).get("built").getInfo()

        built_areas.append(area or 0.0)

    # Growth rates
    growth_rates = compute_growth_rates(built_areas, years)

    # Expansion direction (for latest year)
    latest_year = years[-1]
    expansion = compute_expansion_direction(
        built_masks[latest_year], geometry, scale, center_point
    )

    # Distance profile (for latest year)
    distance_profile = compute_distance_profile(
        built_masks[latest_year], geometry, center_point, scale
    )

    # Yearly distance profiles for comparison
    yearly_profiles = {}
    for year in years:
        yearly_profiles[year] = compute_distance_profile(
            built_masks[year], geometry, center_point, scale
        )

    return {
        "years": years,
        "yearly_built_area_km2": dict(zip(years, built_areas)),
        "growth_rates": growth_rates,
        "expansion_direction": expansion,
        "distance_profile_latest": distance_profile,
        "yearly_distance_profiles": yearly_profiles,
        "center_point": center_point.coordinates().getInfo(),
    }