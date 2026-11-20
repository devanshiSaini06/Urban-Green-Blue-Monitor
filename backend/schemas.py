"""
Pydantic schemas for API request/response validation.
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from config import STUDY_YEARS, SEASON_WINDOWS, ANALYSIS_SCALES, DISTRICTS, DEFAULT_THRESHOLDS, SpectralThresholds


# =============================================================================
# COMMON SCHEMAS
# =============================================================================
class BoundingBox(BaseModel):
    west: float
    south: float
    east: float
    north: float


class DistrictInfo(BaseModel):
    id: str
    name: str
    display_name: str
    bounds: BoundingBox
    center: List[float]
    zoom: int


class QualityFlags(BaseModel):
    low_image_count: bool = False
    low_coverage: bool = False
    outlier_flag: bool = False
    outlier_details: Optional[str] = None
    images_used: int = 0
    valid_coverage_pct: float = 0.0


class YearlyStats(BaseModel):
    year: int
    images_used: int
    valid_km2: float
    vegetation_km2: float
    water_km2: float
    built_bare_km2: float
    other_km2: float
    vegetation_pct: float
    water_pct: float
    built_bare_pct: float
    other_pct: float
    mean_ndvi: float
    mean_mndwi: float
    mean_ndbi: float
    composite_first_date: Optional[str] = None
    composite_last_date: Optional[str] = None
    quality: QualityFlags
    raw_district_km2: float


class LandCoverClass(str, Enum):
    water = "water"
    vegetation = "vegetation"
    built_bare = "built_bare"
    other = "other"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================
class SeasonWindow(BaseModel):
    name: str = Field(pattern="^(oct-dec|jan-mar|mar-may|jun-sep|custom)$")
    start_month: Optional[int] = Field(default=None, ge=1, le=12)
    end_month: Optional[int] = Field(default=None, ge=1, le=12)  # exclusive
    custom_start: Optional[str] = None  # "YYYY-MM-DD"
    custom_end: Optional[str] = None    # "YYYY-MM-DD"

    @field_validator("custom_start", "custom_end", mode="before")
    @classmethod
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be in ISO format YYYY-MM-DD")
        return v


class ThresholdsRequest(BaseModel):
    mndwi_water: float = DEFAULT_THRESHOLDS.mndwi_water
    ndvi_water_max: float = DEFAULT_THRESHOLDS.ndvi_water_max
    ndvi_veg_min: float = DEFAULT_THRESHOLDS.ndvi_veg_min
    ndbi_built_min: float = DEFAULT_THRESHOLDS.ndbi_built_min
    ndvi_built_max: float = DEFAULT_THRESHOLDS.ndvi_built_max


class AnalysisRequest(BaseModel):
    # Region specification (one of)
    district_id: Optional[str] = None
    geojson: Optional[Dict[str, Any]] = None  # GeoJSON Feature or FeatureCollection

    # Time parameters
    years: List[int] = Field(default_factory=lambda: STUDY_YEARS)
    season: SeasonWindow = Field(default_factory=lambda: SeasonWindow(name="oct-dec"))
    baseline_year: Optional[int] = None

    # Processing parameters
    classifier: Literal["spectral", "dynamic_world"] = "spectral"
    thresholds: ThresholdsRequest = Field(default_factory=ThresholdsRequest)
    cloud_threshold: int = Field(default=80, ge=0, le=100)
    scale: int = Field(default=20)

    # Options
    include_transitions: bool = False
    include_landscape_metrics: bool = False
    include_urban_growth: bool = False
    include_environmental: bool = False

    @field_validator("years")
    @classmethod
    def validate_years(cls, v):
        for year in v:
            if year not in STUDY_YEARS:
                raise ValueError(f"Year {year} not in study period {STUDY_YEARS}")
        return sorted(list(set(v)))

    @field_validator("scale")
    @classmethod
    def validate_scale(cls, v):
        if v not in ANALYSIS_SCALES:
            raise ValueError(f"Scale must be one of {ANALYSIS_SCALES}")
        return v

    @field_validator("baseline_year")
    @classmethod
    def validate_baseline(cls, v, info):
        if v is not None and "years" in info.data and v not in info.data["years"]:
            raise ValueError("Baseline year must be in the selected years")
        return v


class TileRequest(BaseModel):
    layer: Literal[
        "true_color", "ndvi", "mndwi", "ndbi",
        "landcover", "change_since_baseline", "year_to_year"
    ]
    year: int
    district_id: Optional[str] = None
    geojson: Optional[Dict[str, Any]] = None
    classifier: Literal["spectral", "dynamic_world"] = "spectral"
    thresholds: Optional[ThresholdsRequest] = None
    baseline_year: Optional[int] = None
    compare_year: Optional[int] = None  # For year_to_year layer


class ValidateRequest(BaseModel):
    district_id: Optional[str] = None
    geojson: Optional[Dict[str, Any]] = None
    year: int = 2020
    classifier: Literal["spectral", "dynamic_world"] = "spectral"
    thresholds: Optional[ThresholdsRequest] = None
    reference_points_csv: Optional[str] = None  # Base64 encoded CSV


class TrendRequest(BaseModel):
    district_id: Optional[str] = None
    geojson: Optional[Dict[str, Any]] = None
    years: List[int] = Field(default_factory=lambda: STUDY_YEARS)
    season: SeasonWindow = Field(default_factory=lambda: SeasonWindow(name="oct-dec"))
    classifier: Literal["spectral", "dynamic_world"] = "spectral"
    thresholds: Optional[ThresholdsRequest] = None
    variable: Literal["vegetation", "water", "built_bare", "ndvi", "mndwi", "ndbi"] = "vegetation"


class ReportRequest(BaseModel):
    district_id: Optional[str] = None
    geojson: Optional[Dict[str, Any]] = None
    years: List[int] = Field(default_factory=lambda: STUDY_YEARS)
    season: SeasonWindow = Field(default_factory=lambda: SeasonWindow(name="oct-dec"))
    classifier: Literal["spectral", "dynamic_world"] = "spectral"
    thresholds: Optional[ThresholdsRequest] = None
    baseline_year: Optional[int] = None
    include_maps: bool = True
    title: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: int = 0  # 0-100
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================
class AnalysisResponse(BaseModel):
    district_id: Optional[str] = None
    geojson_bounds: Optional[BoundingBox] = None
    years: List[int]
    season: SeasonWindow
    classifier: str
    thresholds: ThresholdsRequest
    scale: int
    baseline_year: Optional[int]
    stats: List[YearlyStats]
    recommended_baseline_year: int
    quality_summary: Dict[str, Any]
    run_metadata: Dict[str, Any]


class TileResponse(BaseModel):
    tile_url: str
    token: str
    expires_at: datetime
    bounds: BoundingBox
    min_zoom: int
    max_zoom: int


class ValidateResponse(BaseModel):
    confusion_matrix: List[List[int]]
    classes: List[str]
    overall_accuracy: float
    balanced_accuracy: float
    producers_accuracy: Dict[str, float]
    users_accuracy: Dict[str, float]
    kappa: float
    sample_size: int
    reference_source: str
    warnings: List[str]


class TrendResponse(BaseModel):
    variable: str
    years: List[int]
    values: List[float]
    mann_kendall: Dict[str, Any]
    sen_slope: Dict[str, Any]
    linear_regression: Dict[str, Any]
    interpretation: str
    warnings: List[str]


class TransitionMatrixResponse(BaseModel):
    from_year: int
    to_year: int
    classes: List[str]
    matrix_km2: List[List[float]]
    matrix_pct: List[List[float]]
    net_change: Dict[str, float]


class LandscapeMetricsResponse(BaseModel):
    year: int
    patch_count: int
    mean_patch_size_km2: float
    largest_patch_index: float
    total_class_area_km2: float


class UrbanGrowthResponse(BaseModel):
    yearly_growth_rate: List[Dict[str, Any]]
    expansion_direction: List[Dict[str, Any]]  # Rose diagram data
    distance_profile: List[Dict[str, Any]]     # Distance from center


class EnvironmentalResponse(BaseModel):
    correlations: Dict[str, float]
    lst_trend: Optional[List[Dict[str, Any]]] = None
    ntl_trend: Optional[List[Dict[str, Any]]] = None
    population_trend: Optional[List[Dict[str, Any]]] = None
    rainfall_trend: Optional[List[Dict[str, Any]]] = None


class ReportResponse(BaseModel):
    pdf_base64: str
    filename: str


class LakesResponse(BaseModel):
    lakes: List[Dict[str, Any]]
    flagged_lakes: List[Dict[str, Any]]
    summary: Dict[str, Any]


class HotspotsResponse(BaseModel):
    vegetation_loss: List[Dict[str, Any]]
    built_up_gain: List[Dict[str, Any]]
    grid_size_km: float


