"""
Main FastAPI application for Urban Green and Blue Change Monitor.
"""
import asyncio
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from config import (
    API_HOST, API_PORT, CORS_ORIGINS, STUDY_YEARS, DISTRICTS,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS,
    MAX_UPLOAD_SIZE_MB, ALLOWED_UPLOAD_EXTENSIONS,
    GEE_PROJECT_ID
)
from schemas import (
    AnalysisRequest, AnalysisResponse, TileRequest, TileResponse,
    ValidateRequest, ValidateResponse, TrendRequest, TrendResponse,
    ReportRequest, ReportResponse, JobStatus,
    TransitionMatrixResponse, LandscapeMetricsResponse,
    UrbanGrowthResponse, EnvironmentalResponse,
    LakesResponse, HotspotsResponse, DistrictInfo, BoundingBox
)
from gee_processor import run_analysis, get_tile_url, initialize_gee
from cache import get_cache, build_analysis_cache_key, build_tile_cache_key
from trend_analysis import run_trend_analysis
from accuracy import run_accuracy_assessment
from transitions import run_transition_analysis
from landscape import run_landscape_metrics, run_landscape_time_series
from urban_growth import run_urban_growth_analysis
from environmental import run_environmental_analysis
from lakes import run_lakes_analysis
from hotspots import run_hotspot_analysis
from reports import generate_report

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Job storage (in-memory for local, use Redis in production)
jobs: Dict[str, JobStatus] = {}
jobs_lock = asyncio.Lock()

# Rate limiting (simple in-memory)
rate_limit_store: Dict[str, list] = {}
rate_limit_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Urban Green and Blue Change Monitor API")
    try:
        initialize_gee()
        logger.info("GEE initialized successfully")
    except Exception as e:
        logger.warning(f"GEE initialization failed (will retry on first request): {e}")

    # Start cache cleanup task
    asyncio.create_task(cleanup_cache_periodically())

    yield

    # Shutdown
    logger.info("Shutting down")


app = FastAPI(
    title="Urban Green and Blue Change Monitor",
    description="API for comparing vegetation, surface water and built-up land changes in Indian districts (2018-2025)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
async def check_rate_limit(client_ip: str) -> bool:
    """Simple rate limiting."""
    async with rate_limit_lock:
        now = datetime.now().timestamp()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        if client_ip not in rate_limit_store:
            rate_limit_store[client_ip] = []

        # Remove old entries
        rate_limit_store[client_ip] = [
            ts for ts in rate_limit_store[client_ip] if ts > window_start
        ]

        if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
            return False

        rate_limit_store[client_ip].append(now)
        return True


def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def create_job(status: str = "pending", message: str = "") -> str:
    """Create a new background job."""
    job_id = str(uuid.uuid4())
    job = JobStatus(
        job_id=job_id,
        status=status,
        progress=0,
        message=message,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    async with jobs_lock:
        jobs[job_id] = job
    return job_id


async def update_job(
    job_id: str,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    result: Optional[Dict] = None,
    error: Optional[str] = None
):
    """Update job status."""
    async with jobs_lock:
        if job_id in jobs:
            job = jobs[job_id]
            if status:
                job.status = status
            if progress is not None:
                job.progress = progress
            if message:
                job.message = message
            if result:
                job.result = result
            if error:
                job.error = error
            job.updated_at = datetime.utcnow()


async def run_analysis_background(job_id: str, request: AnalysisRequest):
    """Background task for analysis."""
    try:
        await update_job(job_id, status="running", progress=10, message="Initializing GEE...")

        # Check cache
        cache = get_cache()
        cache_key = build_analysis_cache_key(request.model_dump())
        cached = cache.get("analysis", cache_key)

        if cached:
            await update_job(job_id, status="completed", progress=100, message="Loaded from cache", result=cached)
            return

        await update_job(job_id, progress=30, message="Running analysis...")

        result = await run_analysis(request)

        await update_job(job_id, progress=90, message="Caching results...")

        # Cache result
        cache.set("analysis", cache_key, result)

        await update_job(job_id, status="completed", progress=100, message="Analysis complete", result=result)

    except Exception as e:
        logger.error(f"Analysis job {job_id} failed: {e}")
        await update_job(job_id, status="failed", error=str(e))


async def cleanup_cache_periodically():
    """Periodically clean expired cache entries."""
    while True:
        await asyncio.sleep(3600)  # Every hour
        try:
            cache = get_cache()
            deleted = cache.clear_expired()
            if deleted > 0:
                logger.info(f"Cleaned {deleted} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")


# =============================================================================
# API ENDPOINTS
# =============================================================================
from fastapi.responses import PlainTextResponse

@app.get("/health", response_class=PlainTextResponse)
async def health_check():
    """Health check endpoint."""
    return "healthy"


@app.get("/api/regions", response_model=list[DistrictInfo])
async def get_regions():
    """Get available districts with bounds and metadata."""
    regions = []
    for district_id, config in DISTRICTS.items():
        regions.append(DistrictInfo(
            id=district_id,
            name=config.name,
            display_name=config.display_name,
            bounds=BoundingBox(
                west=config.bounds[0],
                south=config.bounds[1],
                east=config.bounds[2],
                north=config.bounds[3],
            ),
            center=config.center,
            zoom=config.zoom,
        ))
    return regions


@app.post("/api/analysis", response_model=AnalysisResponse)
async def analyze(
    request: AnalysisRequest,
    background: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Run land cover change analysis.
    If background=true, returns job ID for polling.
    """
    # Validate years
    for year in request.years:
        if year not in STUDY_YEARS:
            raise HTTPException(400, f"Year {year} not in study period {STUDY_YEARS}")

    if background:
        job_id = await create_job(message="Queued for processing")
        background_tasks.add_task(run_analysis_background, job_id, request)
        return {"job_id": job_id, "status": "pending"}

    # Check cache
    cache = get_cache()
    cache_key = build_analysis_cache_key(request.model_dump())
    cached = cache.get("analysis", cache_key)

    if cached:
        return AnalysisResponse(**cached)

    # Run analysis
    result = await run_analysis(request)

    # Cache result
    cache.set("analysis", cache_key, result)

    return AnalysisResponse(**result)


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """Get background job status."""
    async with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(404, "Job not found")
        return jobs[job_id]


@app.post("/api/tiles", response_model=TileResponse)
async def get_tiles(request: TileRequest):
    """Get map tile URL for a layer."""
    # Validate year
    if request.year not in STUDY_YEARS:
        raise HTTPException(400, f"Year {request.year} not in study period")

    # Check cache
    cache = get_cache()
    cache_key = build_tile_cache_key(request.layer, request.year, request.model_dump())
    cached = cache.get("tiles", cache_key)

    if cached:
        return TileResponse(**cached)

    # Get geometry
    if request.district_id:
        from gee_processor import get_district_geometry
        geometry = get_district_geometry(request.district_id)
    elif request.geojson:
        from gee_processor import geojson_to_geometry
        geometry = geojson_to_geometry(request.geojson)
    else:
        raise HTTPException(400, "Either district_id or geojson required")

    # Convert season dict to SeasonWindow model if needed
    from schemas import SeasonWindow, AnalysisRequest, ThresholdsRequest
    season = request.season if isinstance(request.season, SeasonWindow) else SeasonWindow(**request.season)

    # Build an AnalysisRequest for get_tile_url
    analysis_request = AnalysisRequest(
        district_id=request.district_id,
        geojson=request.geojson,
        years=[request.year],
        season=season,
        classifier=request.classifier,
        thresholds=request.thresholds or ThresholdsRequest(),
        cloud_threshold=80,
        scale=20,
    )

    # Generate tile URL
    result = get_tile_url(
        request.layer,
        request.year,
        geometry,
        analysis_request,
        request.compare_year
    )

    # Cache
    cache.set("tiles", cache_key, result)

    return TileResponse(**result)


@app.post("/api/validate", response_model=ValidateResponse)
async def validate(request: ValidateRequest):
    """Run accuracy assessment."""
    # Validate year
    if request.year not in STUDY_YEARS:
        raise HTTPException(400, f"Year {request.year} not in study period")

    result = await run_accuracy_assessment(request)
    return ValidateResponse(
        confusion_matrix=result.confusion_matrix,
        classes=result.classes,
        overall_accuracy=result.overall_accuracy,
        balanced_accuracy=result.balanced_accuracy,
        producers_accuracy=result.producers_accuracy,
        users_accuracy=result.users_accuracy,
        kappa=result.kappa,
        sample_size=result.sample_size,
        reference_source="WorldCover" if not request.reference_points_csv else "User-provided",
        warnings=[] if request.year in [2020, 2021] else [
            f"WorldCover reference not available for {request.year}. Using user-provided points or no validation."
        ]
    )


@app.post("/api/trend", response_model=TrendResponse)
async def trend(request: TrendRequest):
    """Run trend analysis."""
    # Validate years
    for year in request.years:
        if year not in STUDY_YEARS:
            raise HTTPException(400, f"Year {year} not in study period")

    # First run analysis to get values
    analysis_request = AnalysisRequest(
        district_id=request.district_id,
        geojson=request.geojson,
        years=request.years,
        season=request.season,
        classifier=request.classifier,
        thresholds=request.thresholds,
    )

    analysis_result = await run_analysis(analysis_request)

    # Extract values for the requested variable
    variable_map = {
        "vegetation": "vegetation_pct",
        "water": "water_pct",
        "built_bare": "built_bare_pct",
        "ndvi": "mean_ndvi",
        "mndwi": "mean_mndwi",
        "ndbi": "mean_ndbi",
    }

    var_key = variable_map[request.variable]
    values = [s[var_key] for s in analysis_result["stats"]]

    # Run trend analysis
    result = run_trend_analysis(values, request.years, request.variable)

    return TrendResponse(**result)


@app.post("/api/transitions", response_model=TransitionMatrixResponse)
async def transitions(request: TrendRequest):
    """Run land cover transition analysis."""
    # This endpoint needs from_year and to_year - using first and last for now
    # In practice, this would be a separate request model
    if len(request.years) < 2:
        raise HTTPException(400, "Need at least 2 years for transition analysis")

    from_year = request.years[0]
    to_year = request.years[-1]

    result = await run_transition_analysis(
        request.district_id,
        request.geojson,
        from_year,
        to_year,
        request.season.name,
        request.classifier,
        request.thresholds,
    )

    return TransitionMatrixResponse(**result)


@app.post("/api/landscape", response_model=list[LandscapeMetricsResponse])
async def landscape(request: TrendRequest):
    """Run landscape metrics for vegetation."""
    results = await run_landscape_time_series(
        request.district_id,
        request.geojson,
        request.years,
        request.season.name,
        request.classifier,
        request.thresholds,
    )

    return [LandscapeMetricsResponse(**r) for r in results]


@app.post("/api/urban-growth", response_model=UrbanGrowthResponse)
async def urban_growth(request: TrendRequest):
    """Run urban growth analysis."""
    result = await run_urban_growth_analysis(
        request.district_id,
        request.geojson,
        request.years,
        request.season.name,
        request.classifier,
        request.thresholds,
    )

    return UrbanGrowthResponse(**result)


@app.post("/api/environmental", response_model=EnvironmentalResponse)
async def environmental(request: TrendRequest):
    """Run environmental context analysis."""
    # First get built-up areas from analysis
    analysis_request = AnalysisRequest(
        district_id=request.district_id,
        geojson=request.geojson,
        years=request.years,
        season=request.season,
        classifier=request.classifier,
        thresholds=request.thresholds,
    )

    analysis_result = await run_analysis(analysis_request)
    built_areas = [s["built_bare_km2"] for s in analysis_result["stats"]]

    result = await run_environmental_analysis(
        request.district_id,
        request.geojson,
        request.years,
        built_areas,
    )

    return EnvironmentalResponse(**result)


@app.post("/api/lakes", response_model=LakesResponse)
async def lakes(request: TrendRequest):
    """Run lakes analysis."""
    result = await run_lakes_analysis(
        request.district_id,
        request.geojson,
        request.years,
        request.season.name,
        request.classifier,
        request.thresholds,
    )

    return LakesResponse(**result)


@app.post("/api/hotspots", response_model=HotspotsResponse)
async def hotspots(request: TrendRequest):
    """Run hotspot analysis."""
    if len(request.years) < 2:
        raise HTTPException(400, "Need at least 2 years for hotspot analysis")

    from_year = request.years[0]
    to_year = request.years[-1]

    result = await run_hotspot_analysis(
        request.district_id,
        request.geojson,
        from_year,
        to_year,
        request.season.name,
        request.classifier,
        request.thresholds,
    )

    return HotspotsResponse(**result)


@app.post("/api/report", response_model=ReportResponse)
async def report(request: ReportRequest):
    """Generate PDF report."""
    result = await generate_report(request)
    return ReportResponse(**result)


# =============================================================================
# STATIC FILE SERVING (for local development)
# =============================================================================
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Urban Green and Blue Change Monitor",
        "version": "1.0.0",
        "study_period": f"{STUDY_YEARS[0]}-{STUDY_YEARS[-1]}",
        "districts": list(DISTRICTS.keys()),
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)