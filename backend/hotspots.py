"""
Hotspot module: grid each district (e.g., 1km cells) and map/rank cells
with largest vegetation loss and built-up gain.
"""
import ee
from typing import Dict, List, Any

from gee_processor import (
    initialize_gee, get_district_geometry, geojson_to_geometry,
    get_season_dates, classify_spectral, classify_dynamic_world,
    dynamic_world_to_landcover, compute_indices, SpectralThresholds,
    simplify_geometry, get_sentinel_collection
)
from config import SEASON_WINDOWS
from schemas import ThresholdsRequest


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


def create_grid(
    geometry: ee.Geometry,
    cell_size_km: float = 1.0,
    crs: str = "EPSG:32643"
) -> ee.FeatureCollection:
    """Create a square grid covering the geometry."""
    # Get bounds in the target CRS
    bounds = geometry.bounds(crs=crs, maxError=1000)

    # Get coordinates
    coords = bounds.coordinates().getInfo()[0]
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Cell size in meters
    cell_size_m = cell_size_km * 1000

    # Generate grid features
    # We'll create this in Python and send as FeatureCollection
    features = []
    x = min_x
    cell_id = 0
    while x < max_x:
        y = min_y
        while y < max_y:
            # Create square polygon
            ring = ee.List([
                [x, y],
                [x + cell_size_m, y],
                [x + cell_size_m, y + cell_size_m],
                [x, y + cell_size_m],
                [x, y]
            ])
            cell_geom = ee.Geometry.Polygon(ring, crs=crs)

            # Check intersection with geometry
            # We'll filter later
            feature = ee.Feature(cell_geom, {"cell_id": cell_id, "col": int((x - min_x) / cell_size_m), "row": int((y - min_y) / cell_size_m)})
            features.append(feature)
            cell_id += 1
            y += cell_size_m
        x += cell_size_m

    return ee.FeatureCollection(features)


def compute_hotspots(
    from_image: ee.Image,
    to_image: ee.Image,
    geometry: ee.Geometry,
    cell_size_km: float = 1.0,
    scale: int = 20,
    top_n: int = 20
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Compute vegetation loss and built-up gain hotspots on a grid.
    """
    # Vegetation is class 2, Built is class 3

    # Vegetation loss: was veg (2), now not veg
    veg_loss = from_image.eq(2).And(to_image.neq(2)).rename("veg_loss")

    # Built gain: was not built (3), now built
    built_gain = from_image.neq(3).And(to_image.eq(3)).rename("built_gain")

    # Create grid
    grid = create_grid(geometry, cell_size_km)

    # Add pixel area
    pixel_area = ee.Image.pixelArea().divide(1e6)  # km²

    # For each change type, reduce to grid
    veg_loss_with_area = veg_loss.multiply(pixel_area).rename("veg_loss_km2")
    built_gain_with_area = built_gain.multiply(pixel_area).rename("built_gain_km2")

    # Reduce to grid using reduceRegions
    veg_stats = veg_loss_with_area.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.sum(),
        scale=scale,
        crs="EPSG:32643"
    )

    built_stats = built_gain_with_area.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.sum(),
        scale=scale,
        crs="EPSG:32643"
    )

    # Get results
    veg_features = veg_stats.getInfo()["features"]
    built_features = built_stats.getInfo()["features"]

    # Parse results
    veg_results = []
    for f in veg_features:
        props = f["properties"]
        area = props.get("sum", 0) or 0
        if area > 0:
            veg_results.append({
                "cell_id": props["cell_id"],
                "col": props["col"],
                "row": props["row"],
                "veg_loss_km2": area,
                "geometry": f["geometry"],
            })

    built_results = []
    for f in built_features:
        props = f["properties"]
        area = props.get("sum", 0) or 0
        if area > 0:
            built_results.append({
                "cell_id": props["cell_id"],
                "col": props["col"],
                "row": props["row"],
                "built_gain_km2": area,
                "geometry": f["geometry"],
            })

    # Sort and take top N
    veg_results.sort(key=lambda x: x["veg_loss_km2"], reverse=True)
    built_results.sort(key=lambda x: x["built_gain_km2"], reverse=True)

    return {
        "vegetation_loss": veg_results[:top_n],
        "built_up_gain": built_results[:top_n],
        "grid_cell_size_km": cell_size_km,
        "total_cells_analyzed": len(veg_features),
    }


async def run_hotspot_analysis(
    district_id: str,
    geojson: Dict,
    from_year: int,
    to_year: int,
    season: str,
    classifier: str,
    thresholds: ThresholdsRequest,
    scale: int = 20,
    cloud_threshold: int = 80,
    cell_size_km: float = 1.0,
    top_n: int = 20
) -> Dict[str, Any]:
    """Run complete hotspot analysis between two years."""
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

    # Compute hotspots
    hotspots = compute_hotspots(
        from_image, to_image, geometry, cell_size_km, scale, top_n
    )

    return {
        "from_year": from_year,
        "to_year": to_year,
        "cell_size_km": cell_size_km,
        "top_n": top_n,
        **hotspots,
    }