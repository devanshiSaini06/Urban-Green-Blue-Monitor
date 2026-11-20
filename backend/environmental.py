"""
Environmental context module (optional).
Fetches Landsat LST, VIIRS night-time lights, WorldPop population, CHIRPS rainfall.
"""
import ee
from typing import Dict, List, Any, Optional
import numpy as np

from gee_processor import (
    initialize_gee, get_district_geometry, geojson_to_geometry,
    simplify_geometry
)
from config import STUDY_YEARS


def get_lst_trend(
    geometry: ee.Geometry,
    years: List[int],
    scale: int = 1000  # Landsat LST is ~1000m
) -> List[Dict[str, Any]]:
    """Get Landsat Land Surface Temperature trend."""
    initialize_gee()

    simple_geom = simplify_geometry(geometry)

    # Landsat Collection 2 Surface Temperature
    # Use LANDSAT/LC09/C02/T1_L2 for Landsat 9, LANDSAT/LC08/C02/T1_L2 for Landsat 8
    # ST_B10 is the surface temperature band (in Kelvin * 0.00341802 + 149.0)
    lst_collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                      .merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
                      .filterBounds(simple_geom))

    results = []
    for year in years:
        start = f"{year}-01-01"
        end = f"{year + 1}-01-01"

        yearly = lst_collection.filterDate(start, end)

        # Apply scaling for ST_B10
        def scale_lst(img):
            st = img.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15)  # Celsius
            return img.addBands(st.rename("LST_C")).copyProperties(img, ["system:time_start"])

        yearly = yearly.map(scale_lst)

        # Median composite
        median_lst = yearly.select("LST_C").median().clip(simple_geom)

        # Mean LST
        mean_lst = median_lst.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=simple_geom,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True
        ).get("LST_C").getInfo()

        results.append({
            "year": year,
            "mean_lst_celsius": mean_lst,
        })

    return results


def get_ntl_trend(
    geometry: ee.Geometry,
    years: List[int],
    scale: int = 500  # VIIRS is ~500m
) -> List[Dict[str, Any]]:
    """Get VIIRS Night-time Lights trend."""
    initialize_gee()

    simple_geom = simplify_geometry(geometry)

    # VIIRS Nighttime Day/Night Band Composites
    ntl_collection = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")

    results = []
    for year in years:
        start = f"{year}-01-01"
        end = f"{year + 1}-01-01"

        yearly = ntl_collection.filterBounds(simple_geom).filterDate(start, end)

        # Use 'avg_rad' band (average radiance)
        median_ntl = yearly.select("avg_rad").median().clip(simple_geom)

        mean_ntl = median_ntl.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=simple_geom,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True
        ).get("avg_rad").getInfo()

        results.append({
            "year": year,
            "mean_ntl_radiance": mean_ntl,
        })

    return results


def get_population_trend(
    geometry: ee.Geometry,
    years: List[int],
    scale: int = 1000  # WorldPop is ~100m, aggregate to 1km
) -> List[Dict[str, Any]]:
    """Get WorldPop population trend."""
    initialize_gee()

    simple_geom = simplify_geometry(geometry)

    # WorldPop population count (unconstrained)
    pop_collection = ee.ImageCollection("WorldPop/GP/100m/pop")

    results = []
    for year in years:
        # WorldPop has data for specific years
        # Filter to closest year
        pop_img = pop_collection.filter(
            ee.Filter.calendarRange(year, year, "year")
        ).first()

        if pop_img:
            # Clip and reduce
            clipped = pop_img.clip(simple_geom)
            total_pop = clipped.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=simple_geom,
                scale=scale,
                maxPixels=1e13,
                bestEffort=True
            ).get("population").getInfo()

            results.append({
                "year": year,
                "total_population": total_pop,
            })
        else:
            results.append({
                "year": year,
                "total_population": None,
            })

    return results


def get_rainfall_trend(
    geometry: ee.Geometry,
    years: List[int],
    scale: int = 5000  # CHIRPS is ~5km
) -> List[Dict[str, Any]]:
    """Get CHIRPS rainfall trend."""
    initialize_gee()

    simple_geom = simplify_geometry(geometry)

    # CHIRPS daily precipitation
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")

    results = []
    for year in years:
        start = f"{year}-01-01"
        end = f"{year + 1}-01-01"

        yearly = chirps.filterBounds(simple_geom).filterDate(start, end)

        # Sum annual precipitation
        annual = yearly.sum().clip(simple_geom)

        mean_annual = annual.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=simple_geom,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True
        ).get("precipitation").getInfo()

        results.append({
            "year": year,
            "annual_rainfall_mm": mean_annual,
        })

    return results


def compute_correlations(
    built_areas: List[float],
    lst_data: List[Dict],
    ntl_data: List[Dict],
    pop_data: List[Dict],
    rain_data: List[Dict],
    years: List[int]
) -> Dict[str, float]:
    """Compute correlations between built-up and environmental variables."""
    correlations = {}

    # Helper to extract values aligned by year
    def extract_series(data: List[Dict], key: str) -> List[float]:
        year_to_val = {d["year"]: d.get(key) for d in data}
        return [year_to_val.get(y, 0) for y in years]

    built_series = built_areas

    lst_series = extract_series(lst_data, "mean_lst_celsius")
    ntl_series = extract_series(ntl_data, "mean_ntl_radiance")
    pop_series = extract_series(pop_data, "total_population")
    rain_series = extract_series(rain_data, "annual_rainfall_mm")

    # Filter out None values
    def safe_corr(x, y):
        valid = [(xi, yi) for xi, yi in zip(x, y) if xi is not None and yi is not None]
        if len(valid) < 3:
            return None
        xv, yv = zip(*valid)
        return np.corrcoef(xv, yv)[0, 1]

    correlations["built_vs_lst"] = safe_corr(built_series, lst_series)
    correlations["built_vs_ntl"] = safe_corr(built_series, ntl_series)
    correlations["built_vs_population"] = safe_corr(built_series, pop_series)
    correlations["built_vs_rainfall"] = safe_corr(built_series, rain_series)

    return correlations


async def run_environmental_analysis(
    district_id: str,
    geojson: Dict,
    years: List[int],
    built_areas: List[float],
    scale: int = 1000
) -> Dict[str, Any]:
    """Run complete environmental context analysis."""
    initialize_gee()

    # Get geometry
    if district_id:
        geometry = get_district_geometry(district_id)
    else:
        geometry = geojson_to_geometry(geojson)

    # Fetch all environmental data
    lst_trend = get_lst_trend(geometry, years, scale)
    ntl_trend = get_ntl_trend(geometry, years, scale)
    pop_trend = get_population_trend(geometry, years, scale)
    rain_trend = get_rainfall_trend(geometry, years, scale)

    # Compute correlations
    correlations = compute_correlations(
        built_areas, lst_trend, ntl_trend, pop_trend, rain_trend, years
    )

    return {
        "correlations": correlations,
        "lst_trend": lst_trend,
        "ntl_trend": ntl_trend,
        "population_trend": pop_trend,
        "rainfall_trend": rain_trend,
    }