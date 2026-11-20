"""
Accuracy assessment module for land cover classification.
Compares against ESA WorldCover and user-provided reference data.
"""
import ee
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import base64
import io
import csv

from config import WORLDCOVER_VERSIONS, STRATIFIED_SAMPLE_PER_CLASS, RANDOM_SAMPLE_SIZE
from schemas import ValidateRequest, ThresholdsRequest
from gee_processor import (
    initialize_gee, get_district_geometry, geojson_to_geometry,
    get_season_dates, classify_spectral, classify_dynamic_world,
    dynamic_world_to_landcover, compute_indices, SpectralThresholds,
    simplify_geometry
)
from config import SEASON_WINDOWS

# WorldCover class mapping to our 4 classes
# WorldCover v100/v200 classes:
# 10: Tree cover, 20: Shrubland, 30: Grassland, 40: Cropland,
# 50: Built-up, 60: Bare/sparse vegetation, 70: Snow/ice,
# 80: Permanent water bodies, 90: Herbaceous wetland, 95: Mangroves,
# 100: Moss/lichen
WC_TO_OUR_CLASSES = {
    10: 2,   # Tree cover -> vegetation
    20: 2,   # Shrubland -> vegetation
    30: 2,   # Grassland -> vegetation
    40: 2,   # Cropland -> vegetation
    50: 3,   # Built-up -> built_bare
    60: 3,   # Bare -> built_bare
    70: 4,   # Snow -> other
    80: 1,   # Water -> water
    90: 1,   # Wetland -> water
    95: 2,   # Mangroves -> vegetation
    100: 4,  # Moss/lichen -> other
}

OUR_CLASS_NAMES = {1: "water", 2: "vegetation", 3: "built_bare", 4: "other"}


@dataclass
class AccuracyResult:
    confusion_matrix: List[List[int]]
    classes: List[str]
    overall_accuracy: float
    balanced_accuracy: float
    producers_accuracy: Dict[str, float]
    users_accuracy: Dict[str, float]
    kappa: float
    sample_size: int


def get_worldcover_image(year: int) -> ee.Image:
    """Get WorldCover image for a given year (2020 or 2021)."""
    if year not in WORLDCOVER_VERSIONS:
        raise ValueError(f"WorldCover not available for year {year}. Available: {list(WORLDCOVER_VERSIONS.keys())}")
    return ee.Image(WORLDCOVER_VERSIONS[year]).select("Map")


def remap_worldcover(wc_image: ee.Image) -> ee.Image:
    """Remap WorldCover classes to our 4 classes."""
    # Create remapping
    from_vals = list(WC_TO_OUR_CLASSES.keys())
    to_vals = list(WC_TO_OUR_CLASSES.values())
    return wc_image.remap(from_vals, to_vals, 4).rename("reference").byte()


def get_classification_image(
    geometry: ee.Geometry,
    year: int,
    season_name: str,
    classifier: str,
    thresholds: ThresholdsRequest
) -> ee.Image:
    """Get our classification for a given year."""
    initialize_gee()

    # Get season dates (use oct-dec default if not specified)
    from config import SEASON_WINDOWS
    start_month, end_month = SEASON_WINDOWS.get(season_name, SEASON_WINDOWS["oct-dec"])

    if end_month == 1:
        start_date = f"{year}-{start_month:02d}-01"
        end_date = f"{year + 1}-01-01"
    else:
        start_date = f"{year}-{start_month:02d}-01"
        end_date = f"{year}-{end_month:02d}-01"

    simple_geom = simplify_geometry(geometry)

    if classifier == "spectral":
        from gee_processor import get_sentinel_collection
        collection = get_sentinel_collection(simple_geom, start_date, end_date)
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


def stratified_sample(
    reference: ee.Image,
    classification: ee.Image,
    geometry: ee.Geometry,
    points_per_class: int = STRATIFIED_SAMPLE_PER_CLASS,
    scale: int = 20
) -> ee.FeatureCollection:
    """Generate stratified random sample by reference class."""
    # Stack reference and classification
    stacked = reference.addBands(classification).rename(["reference", "predicted"])

    samples = []
    for class_val in [1, 2, 3, 4]:
        class_mask = reference.eq(class_val)
        # Sample points in this class
        class_samples = stacked.updateMask(class_mask).stratifiedSample(
            numPoints=points_per_class,
            classBand="reference",
            region=geometry,
            scale=scale,
            geometries=True,
            seed=42
        )
        samples.append(class_samples)

    return ee.FeatureCollection(samples).flatten()


def random_sample(
    reference: ee.Image,
    classification: ee.Image,
    geometry: ee.Geometry,
    num_points: int = RANDOM_SAMPLE_SIZE,
    scale: int = 20
) -> ee.FeatureCollection:
    """Generate random sample across the entire area."""
    stacked = reference.addBands(classification).rename(["reference", "predicted"])
    return stacked.stratifiedSample(
        numPoints=num_points,
        classBand="reference",
        region=geometry,
        scale=scale,
        geometries=True,
        seed=123
    )


def compute_confusion_matrix(
    samples: ee.FeatureCollection
) -> Tuple[np.ndarray, List[str]]:
    """Compute confusion matrix from sampled points."""
    # Get reference and predicted values
    data = samples.aggregate_array("reference").getInfo()
    pred = samples.aggregate_array("predicted").getInfo()

    # Convert to numpy
    y_true = np.array(data)
    y_pred = np.array(pred)

    # Confusion matrix (4x4)
    cm = np.zeros((4, 4), dtype=int)
    for i in range(4):
        for j in range(4):
            cm[i, j] = np.sum((y_true == i + 1) & (y_pred == j + 1))

    classes = [OUR_CLASS_NAMES[i + 1] for i in range(4)]
    return cm, classes


def calculate_accuracies(cm: np.ndarray, classes: List[str]) -> AccuracyResult:
    """Calculate all accuracy metrics from confusion matrix."""
    total = cm.sum()
    if total == 0:
        raise ValueError("Empty confusion matrix")

    # Overall accuracy
    overall = np.trace(cm) / total

    # Producer's accuracy (recall) per class
    producers = {}
    for i, cls in enumerate(classes):
        row_sum = cm[i, :].sum()
        producers[cls] = cm[i, i] / row_sum if row_sum > 0 else 0.0

    # User's accuracy (precision) per class
    users = {}
    for j, cls in enumerate(classes):
        col_sum = cm[:, j].sum()
        users[cls] = cm[j, j] / col_sum if col_sum > 0 else 0.0

    # Balanced accuracy (mean of per-class recall)
    balanced = np.mean(list(producers.values()))

    # Cohen's Kappa
    # Expected agreement
    row_sums = cm.sum(axis=1)
    col_sums = cm.sum(axis=0)
    expected = np.sum(row_sums * col_sums) / (total ** 2)
    kappa = (overall - expected) / (1 - expected) if expected < 1 else 0

    return AccuracyResult(
        confusion_matrix=cm.tolist(),
        classes=classes,
        overall_accuracy=overall,
        balanced_accuracy=balanced,
        producers_accuracy=producers,
        users_accuracy=users,
        kappa=kappa,
        sample_size=int(total),
    )


def parse_reference_csv(csv_base64: str) -> List[Dict[str, Any]]:
    """Parse user-uploaded reference points CSV (base64 encoded)."""
    try:
        csv_data = base64.b64decode(csv_base64).decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        points = []
        for row in reader:
            # Expect columns: lat, lon, reference_class (water/vegetation/built_bare/other)
            points.append({
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "reference": row["reference_class"].lower(),
            })
        return points
    except Exception as e:
        raise ValueError(f"Failed to parse reference CSV: {e}")


def sample_at_points(
    classification: ee.Image,
    points: List[Dict[str, Any]],
    geometry: ee.Geometry
) -> Tuple[List[int], List[int]]:
    """Sample classification at user-provided points."""
    # Create feature collection from points
    features = []
    for i, pt in enumerate(points):
        feat = ee.Feature(
            ee.Geometry.Point([pt["lon"], pt["lat"]]),
            {"reference": pt["reference"], "id": i}
        )
        features.append(feat)

    fc = ee.FeatureCollection(features)

    # Sample classification at points
    sampled = classification.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.first(),
        scale=20
    )

    # Get results
    results = sampled.aggregate_array("landcover").getInfo()
    references = sampled.aggregate_array("reference").getInfo()

    # Map reference strings to class numbers
    ref_map = {"water": 1, "vegetation": 2, "built_bare": 3, "other": 4}
    ref_nums = [ref_map.get(r, 4) for r in references]

    return ref_nums, results


async def run_accuracy_assessment(request: ValidateRequest) -> AccuracyResult:
    """Run complete accuracy assessment."""
    initialize_gee()

    # Get geometry
    if request.district_id:
        geometry = get_district_geometry(request.district_id)
    else:
        geometry = geojson_to_geometry(request.geojson)

    # Get reference data
    if request.reference_points_csv:
        # Use user-provided reference points
        ref_points = parse_reference_csv(request.reference_points_csv)

        # Get our classification
        from gee_processor import get_sentinel_collection, compute_indices
        from config import SEASON_WINDOWS

        season = request.season.name if request.season.name != "custom" else "oct-dec"
        start_month, end_month = SEASON_WINDOWS.get(season, SEASON_WINDOWS["oct-dec"])

        if end_month == 1:
            start_date = f"{request.year}-{start_month:02d}-01"
            end_date = f"{request.year + 1}-01-01"
        else:
            start_date = f"{request.year}-{start_month:02d}-01"
            end_date = f"{request.year}-{end_month:02d}-01"

        if request.classifier == "spectral":
            collection = get_sentinel_collection(geometry, start_date, end_date)
            composite = collection.median().clip(geometry)
            composite = compute_indices(composite)

            thresholds = SpectralThresholds(
                mndwi_water=request.thresholds.mndwi_water if request.thresholds else 0.10,
                ndvi_water_max=request.thresholds.ndvi_water_max if request.thresholds else 0.15,
                ndvi_veg_min=request.thresholds.ndvi_veg_min if request.thresholds else 0.35,
                ndbi_built_min=request.thresholds.ndbi_built_min if request.thresholds else 0.0,
                ndvi_built_max=request.thresholds.ndvi_built_max if request.thresholds else 0.20,
            )
            classified = classify_spectral(composite, thresholds)
        else:
            dw = classify_dynamic_world(geometry, start_date, end_date)
            classified = dynamic_world_to_landcover(dw)

        ref_nums, pred_nums = sample_at_points(classified.select("landcover"), ref_points, geometry)

        # Build confusion matrix
        cm = np.zeros((4, 4), dtype=int)
        for r, p in zip(ref_nums, pred_nums):
            if 1 <= r <= 4 and 1 <= p <= 4:
                cm[r - 1, p - 1] += 1

        classes = [OUR_CLASS_NAMES[i + 1] for i in range(4)]
        return calculate_accuracies(cm, classes)

    else:
        # Use WorldCover (only for 2020/2021)
        if request.year not in WORLDCOVER_VERSIONS:
            raise ValueError(
                f"WorldCover reference only available for {list(WORLDCOVER_VERSIONS.keys())}. "
                f"For other years, please upload reference points CSV."
            )

        wc_image = get_worldcover_image(request.year)
        reference = remap_worldcover(wc_image)

        # Get our classification
        thresholds = request.thresholds or ThresholdsRequest()
        classified = get_classification_image(
            geometry, request.year, request.season.name,
            request.classifier, thresholds
        )

        # Stratified + random sampling
        strat_samples = stratified_sample(reference, classified, geometry)
        rand_samples = random_sample(reference, classified, geometry)

        all_samples = ee.FeatureCollection([strat_samples, rand_samples]).flatten()

        cm, classes = compute_confusion_matrix(all_samples)
        return calculate_accuracies(cm, classes)