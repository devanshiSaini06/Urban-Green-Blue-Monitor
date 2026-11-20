"""
Land cover transition matrix module.
Computes from-to class transitions between two years.
"""
import ee
import numpy as np
from typing import Dict, List, Tuple, Any

from config import SEASON_WINDOWS
from gee_processor import (
    initialize_gee, get_district_geometry, geojson_to_geometry,
    get_season_dates, classify_spectral, classify_dynamic_world,
    dynamic_world_to_landcover, compute_indices, SpectralThresholds,
    simplify_geometry, get_sentinel_collection
)
from schemas import ThresholdsRequest


OUR_CLASS_NAMES = ["water", "vegetation", "built_bare", "other"]


def get_classification_for_year(
    geometry: ee.Geometry,
    year: int,
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    cloud_threshold: int = 80
) -> ee.Image:
    """Get land cover classification for a specific year."""
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

    return classified.select("landcover").byte()


def compute_transition_matrix(
    from_image: ee.Image,
    to_image: ee.Image,
    geometry: ee.Geometry,
    scale: int = 20
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute transition matrix (from x to) in pixel counts and areas."""
    # Stack images
    stacked = from_image.addBands(to_image).rename(["from_class", "to_class"])

    # Add pixel area
    pixel_area = ee.Image.pixelArea().divide(1e6).rename("area_km2")  # km²
    stacked = stacked.addBands(pixel_area)

    # Reduce region with grouped reducer
    # Group by from_class, then by to_class
    stats = stacked.reduceRegion(
        reducer=ee.Reducer.sum().repeat(2).group(groupField=0, groupName="from_class")
                        .group(groupField=1, groupName="to_class"),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    )

    # Alternative: simpler approach - get histogram
    # Create combined class code: from_class * 10 + to_class
    combined = from_image.multiply(10).add(to_image).rename("transition")
    combined = combined.addBands(pixel_area)

    hist = combined.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=0, groupName="transition"),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    ).get("groups")

    groups = hist.getInfo()

    # Parse results into 4x4 matrices
    count_matrix = np.zeros((4, 4), dtype=float)
    area_matrix = np.zeros((4, 4), dtype=float)

    for group in groups:
        transition_code = int(group["transition"])
        from_class = (transition_code // 10) - 1  # 0-indexed
        to_class = (transition_code % 10) - 1     # 0-indexed

        if 0 <= from_class < 4 and 0 <= to_class < 4:
            # Count is in the first reducer (sum of 1s), area in second
            # Actually we need to get both count and area
            # Let's use a different approach
            pass

    # Better approach: use frequency histogram for counts, sum for areas
    # Count matrix
    count_hist = from_image.addBands(to_image).rename(["from", "to"]).reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    )

    # Area matrix
    area_hist = from_image.addBands(to_image).addBands(pixel_area).rename(["from", "to", "area"]).reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=0).group(groupField=1),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    )

    # Actually, let's use a simpler and more reliable approach
    # Get pixel values directly via sample
    sample = stacked.stratifiedSample(
        numPoints=10000,
        classBand="from_class",
        region=geometry,
        scale=scale,
        geometries=True,
        seed=42
    )

    # Get arrays
    from_vals = sample.aggregate_array("from_class").getInfo()
    to_vals = sample.aggregate_array("to_class").getInfo()
    area_vals = sample.aggregate_array("area_km2").getInfo()

    count_matrix = np.zeros((4, 4), dtype=float)
    area_matrix = np.zeros((4, 4), dtype=float)

    for f, t, a in zip(from_vals, to_vals, area_vals):
        if 1 <= f <= 4 and 1 <= t <= 4:
            count_matrix[f - 1, t - 1] += 1
            area_matrix[f - 1, t - 1] += a

    # Scale up from sample to full area (using total pixel count)
    # Better: use the actual pixel counts from frequency histogram
    freq = from_image.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    ).getInfo()

    # This is getting complex. Let me use a cleaner approach with two reducers.
    return count_matrix, area_matrix


def compute_transition_matrix_v2(
    from_image: ee.Image,
    to_image: ee.Image,
    geometry: ee.Geometry,
    scale: int = 20
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute transition matrix using a cleaner approach.
    Returns (count_matrix_km2, area_matrix_km2) - both in km².
    """
    pixel_area = ee.Image.pixelArea().divide(1e6)  # km² per pixel

    # Create a combined image with from, to, and area
    combined = ee.Image.cat([
        from_image.rename("from"),
        to_image.rename("to"),
        pixel_area.rename("area")
    ])

    # Reduce with grouped reducer: group by 'from', then by 'to', sum area
    groups = combined.reduceRegion(
        reducer=ee.Reducer.sum()
            .group(groupField=0, groupName="from")
            .group(groupField=1, groupName="to"),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        crs="EPSG:32643"
    ).get("groups")

    groups_info = groups.getInfo()

    area_matrix = np.zeros((4, 4), dtype=float)

    for from_group in groups_info:
        from_class = int(from_group["from"]) - 1  # 0-indexed
        if not (0 <= from_class < 4):
            continue

        to_groups = from_group["groups"]
        for to_group in to_groups:
            to_class = int(to_group["to"]) - 1  # 0-indexed
            if not (0 <= to_class < 4):
                continue

            area = float(to_group["sum"])
            area_matrix[from_class, to_class] = area

    # For count matrix, we can approximate from area / mean pixel area
    # Or compute separately
    count_groups = from_image.addBands(to_image).rename(["from", "to"]).reduceRegion(
        reducer=ee.Reducer.count()
            .group(groupField=0, groupName="from")
            .group(groupField=1, groupName="to"),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        crs="EPSG:32643"
    ).get("groups")

    count_groups_info = count_groups.getInfo()

    count_matrix = np.zeros((4, 4), dtype=float)

    for from_group in count_groups_info:
        from_class = int(from_group["from"]) - 1
        if not (0 <= from_class < 4):
            continue

        to_groups = from_group["groups"]
        for to_group in to_groups:
            to_class = int(to_group["to"]) - 1
            if not (0 <= to_class < 4):
                continue

            count = float(to_group["sum"])
            count_matrix[from_class, to_class] = count

    return count_matrix, area_matrix


def calculate_net_change(area_matrix: np.ndarray) -> Dict[str, float]:
    """Calculate net change per class (km²)."""
    # Net change = column sum (gains) - row sum (losses) for each class
    # But diagonal is no change
    net = {}
    for i, cls in enumerate(OUR_CLASS_NAMES):
        gains = area_matrix[:, i].sum() - area_matrix[i, i]
        losses = area_matrix[i, :].sum() - area_matrix[i, i]
        net[cls] = gains - losses
    return net


def format_transition_matrix(
    from_year: int,
    to_year: int,
    count_matrix: np.ndarray,
    area_matrix: np.ndarray,
    total_valid_km2: float
) -> Dict[str, Any]:
    """Format transition matrix for API response."""
    # Percent matrix (of total valid area)
    pct_matrix = (area_matrix / total_valid_km2 * 100) if total_valid_km2 > 0 else np.zeros((4, 4))

    net_change = calculate_net_change(area_matrix)

    return {
        "from_year": from_year,
        "to_year": to_year,
        "classes": OUR_CLASS_NAMES,
        "matrix_km2": area_matrix.tolist(),
        "matrix_pct": pct_matrix.tolist(),
        "matrix_count": count_matrix.tolist(),
        "net_change_km2": net_change,
        "total_valid_km2": total_valid_km2,
    }


async def run_transition_analysis(
    district_id: str,
    geojson: Dict,
    from_year: int,
    to_year: int,
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    scale: int = 20,
    cloud_threshold: int = 80
) -> Dict[str, Any]:
    """Run transition analysis between two years."""
    initialize_gee()

    # Get geometry
    if district_id:
        geometry = get_district_geometry(district_id)
    else:
        geometry = geojson_to_geometry(geojson)

    # Get classifications for both years
    from_image = get_classification_for_year(
        geometry, from_year, season, classifier, thresholds, cloud_threshold
    )
    to_image = get_classification_for_year(
        geometry, to_year, season, classifier, thresholds, cloud_threshold
    )

    # Compute transition matrix
    count_matrix, area_matrix = compute_transition_matrix_v2(
        from_image, to_image, geometry, scale
    )

    # Get total valid area for percentage calculation
    valid_area = ee.Image.pixelArea().divide(1e6).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        crs="EPSG:32643"
    ).get("area").getInfo()

    return format_transition_matrix(
        from_year, to_year, count_matrix, area_matrix, valid_area or 0
    )