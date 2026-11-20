"""
Configuration constants for Urban Green and Blue Change Monitor.
Single source of truth for all configurable parameters.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import os


# =============================================================================
# FIXED STUDY PERIOD - Single configuration constant
# =============================================================================
STUDY_YEARS: List[int] = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
MIN_YEAR = min(STUDY_YEARS)
MAX_YEAR = max(STUDY_YEARS)

# Seasonal windows (month_start, month_end_exclusive) - 1-indexed months
SEASON_WINDOWS: Dict[str, tuple] = {
    "oct-dec": (10, 1),    # Oct 1 - Dec 31 (ends Jan 1 next year)
    "jan-mar": (1, 4),     # Jan 1 - Mar 31
    "mar-may": (3, 6),     # Mar 1 - May 31
    "jun-sep": (6, 10),    # Jun 1 - Sep 30
}
DEFAULT_SEASON = "oct-dec"

# =============================================================================
# DISTRICT CONFIGURATION
# =============================================================================
@dataclass(frozen=True)
class DistrictConfig:
    name: str
    display_name: str
    asset_id: str
    feature_index: int
    bounds: List[float]  # [west, south, east, north] in EPSG:4326
    center: List[float]  # [lat, lon] for map centering
    zoom: int


DISTRICTS: Dict[str, DistrictConfig] = {
    "bengaluru_urban": DistrictConfig(
        name="bengaluru_urban",
        display_name="Bengaluru Urban (Karnataka)",
        asset_id="projects/graphic-tide-513321-m3/assets/Bengaluru",
        feature_index=1,
        bounds=[77.2, 12.8, 77.8, 13.3],
        center=[12.97, 77.59],
        zoom=10,
    ),
    "gautam_buddha_nagar": DistrictConfig(
        name="gautam_buddha_nagar",
        display_name="Gautam Buddha Nagar / Greater Noida (Uttar Pradesh)",
        asset_id="projects/graphic-tide-513321-m3/assets/GautamBuddhaNagar",
        feature_index=0,
        bounds=[77.2, 28.2, 77.7, 28.7],
        center=[28.46, 77.49],
        zoom=10,
    ),
}

DEFAULT_DISTRICT = "bengaluru_urban"

# =============================================================================
# SENTINEL-2 PROCESSING PARAMETERS
# =============================================================================
SENTINEL_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
DEFAULT_CLOUD_THRESHOLD = 80  # CLOUDY_PIXEL_PERCENTAGE < 80
SCL_MASK_CLASSES = [0, 1, 3, 8, 9, 10, 11]  # Classes to mask out
KEEP_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]
SCALE_FACTOR = 0.0001

# Analysis scales in meters (selectable)
ANALYSIS_SCALES = [10, 20, 30]
DEFAULT_SCALE = 20
EXPORT_CRS = "EPSG:32643"  # UTM Zone 43N

# =============================================================================
# CLASSIFICATION THRESHOLDS (all adjustable in UI)
# =============================================================================
@dataclass
class SpectralThresholds:
    mndwi_water: float = 0.10
    ndvi_water_max: float = 0.15
    ndvi_veg_min: float = 0.35
    ndbi_built_min: float = 0.0
    ndvi_built_max: float = 0.20


DEFAULT_THRESHOLDS = SpectralThresholds()

# Dynamic World class mapping
DW_CLASS_NAMES = {
    0: "water",
    1: "trees",
    2: "grass",
    3: "flooded_vegetation",
    4: "crops",
    5: "shrub_and_scrub",
    6: "built",
    7: "bare",
    8: "snow",
}

DW_CLASS_TO_LANDCOVER = {
    "water": "water",
    "trees": "vegetation",
    "grass": "vegetation",
    "flooded_vegetation": "water",
    "crops": "vegetation",
    "shrub_and_scrub": "vegetation",
    "built": "built_bare",
    "bare": "built_bare",
    "snow": "other",
}

# =============================================================================
# OUTLIER DETECTION
# =============================================================================
OUTLIER_THRESHOLD_PCT = 25.0  # Flag if year differs from neighbor avg by >25%

# =============================================================================
# QUALITY FLAGS
# =============================================================================
MIN_IMAGES_WARNING = 5  # Warn if fewer images than this
MIN_COVERAGE_PCT_WARNING = 50.0  # Warn if valid coverage < 50%

# =============================================================================
# TREND ANALYSIS
# =============================================================================
TREND_ALPHA = 0.05
TREND_WARNING_N = 8  # Warn that n=8 gives low power

# =============================================================================
# ACCURACY ASSESSMENT
# =============================================================================
WORLDCOVER_VERSIONS = {
    2020: "ESA/WorldCover/v100",
    2021: "ESA/WorldCover/v200",
}
STRATIFIED_SAMPLE_PER_CLASS = 300
RANDOM_SAMPLE_SIZE = 1500

# =============================================================================
# GEE AUTHENTICATION
# =============================================================================
GEE_PROJECT_ID = "graphic-tide-513321-m3"
GEE_SERVICE_ACCOUNT_KEY_PATH = os.getenv("GEE_SERVICE_ACCOUNT_KEY_PATH")
GEE_SERVICE_ACCOUNT_KEY_JSON = os.getenv("GEE_SERVICE_ACCOUNT_KEY_JSON")

# =============================================================================
# CACHING
# =============================================================================
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
CACHE_TTL_DAYS = 30

# =============================================================================
# API SETTINGS
# =============================================================================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW_SECONDS = 60

# Upload limits
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_UPLOAD_EXTENSIONS = {".geojson", ".json", ".zip", ".shp"}

# =============================================================================
# REPORT SETTINGS
# =============================================================================
REPORT_LOGO_PATH = os.getenv("REPORT_LOGO_PATH")
REPORT_FOOTER_TEXT = "Urban Green and Blue Change Monitor | Generated {date}"