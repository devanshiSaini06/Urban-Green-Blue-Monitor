# API Reference

Base URL: `http://localhost:8000` (local) or `https://api.yourdomain.com` (production)

All endpoints return JSON. Errors follow RFC 7807 format.

---

## Authentication

Currently no authentication required for read endpoints. Admin endpoints (future) will use JWT.

---

## Rate Limiting

- **Limit**: 100 requests per minute per IP
- **Window**: 60 seconds
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Regions

### GET /api/regions

List available districts with bounds and metadata.

**Response:**
```json
[
  {
    "id": "bengaluru_urban",
    "name": "bengaluru_urban",
    "display_name": "Bengaluru Urban (Karnataka)",
    "bounds": {"west": 77.2, "south": 12.8, "east": 77.8, "north": 13.3},
    "center": [12.97, 77.59],
    "zoom": 10
  },
  {
    "id": "gautam_buddha_nagar",
    "name": "gautam_buddha_nagar",
    "display_name": "Gautam Buddha Nagar / Greater Noida (Uttar Pradesh)",
    "bounds": {"west": 77.2, "south": 28.2, "east": 77.7, "north": 28.7},
    "center": [28.46, 77.49],
    "zoom": 10
  }
]
```

---

## Analysis

### POST /api/analysis

Run land cover change analysis.

**Request Body:**
```json
{
  "district_id": "bengaluru_urban",
  "geojson": null,
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "season": {
    "name": "oct-dec",
    "start_month": 10,
    "end_month": 1,
    "custom_start": null,
    "custom_end": null
  },
  "baseline_year": 2020,
  "classifier": "spectral",
  "thresholds": {
    "mndwi_water": 0.10,
    "ndvi_water_max": 0.15,
    "ndvi_veg_min": 0.35,
    "ndbi_built_min": 0.0,
    "ndvi_built_max": 0.20
  },
  "cloud_threshold": 80,
  "scale": 20,
  "include_transitions": false,
  "include_landscape_metrics": false,
  "include_urban_growth": false,
  "include_environmental": false
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `district_id` | string | One of* | District identifier |
| `geojson` | object | One of* | Custom GeoJSON Feature/FeatureCollection |
| `years` | int[] | No | Years to analyze (default: all) |
| `season` | object | No | Seasonal window (default: oct-dec) |
| `baseline_year` | int | No | Baseline for change calculations |
| `classifier` | string | No | `"spectral"` or `"dynamic_world"` |
| `thresholds` | object | No | Classification thresholds |
| `cloud_threshold` | int | No | Max cloud % (0-100, default: 80) |
| `scale` | int | No | Analysis scale: 10, 20, or 30 |

*Provide exactly one of `district_id` or `geojson`.

**Response:**
```json
{
  "district_id": "bengaluru_urban",
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "season": {"name": "oct-dec", ...},
  "classifier": "spectral",
  "thresholds": {...},
  "scale": 20,
  "baseline_year": 2020,
  "stats": [
    {
      "year": 2018,
      "images_used": 8,
      "valid_km2": 200.5,
      "vegetation_km2": 50.2,
      "water_km2": 10.1,
      "built_bare_km2": 40.3,
      "other_km2": 100.0,
      "vegetation_pct": 25.0,
      "water_pct": 5.0,
      "built_bare_pct": 20.1,
      "other_pct": 49.9,
      "mean_ndvi": 0.35,
      "mean_mndwi": -0.1,
      "mean_ndbi": 0.05,
      "composite_first_date": "2018-10-15",
      "composite_last_date": "2018-12-20",
      "quality": {
        "low_image_count": false,
        "low_coverage": false,
        "outlier_flag": false,
        "outlier_details": null,
        "images_used": 8,
        "valid_coverage_pct": 85.0
      },
      "raw_district_km2": 220.0
    }
  ],
  "recommended_baseline_year": 2020,
  "quality_summary": {
    "years_with_warnings": 1,
    "outlier_years": [2018],
    "best_quality_year": 2020
  },
  "run_metadata": {
    "run_date": "2024-01-15T10:30:00Z",
    "gee_project": "graphic-tide-513321-m3",
    "sentinel_collection": "COPERNICUS/S2_SR_HARMONIZED",
    "dynamic_world_collection": "GOOGLE/DYNAMICWORLD/V1",
    "scale_m": 20,
    "crs": "EPSG:32643",
    "cloud_threshold": 80,
    "classifier": "spectral",
    "thresholds": {...},
    "season": {...},
    "district": "Bengaluru Urban"
  }
}
```

### POST /api/analysis (Background)

Add `?background=true` to return immediately with a job ID.

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "pending"
}
```

### GET /api/jobs/{job_id}

Poll for background job status.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "progress": 100,
  "message": "Analysis complete",
  "result": {...},
  "error": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:45Z"
}
```

---

## Map Tiles

### GET /api/tiles

Get map tile URL for a layer.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `layer` | string | Yes | `true_color`, `ndvi`, `mndwi`, `ndbi`, `landcover`, `change_since_baseline`, `year_to_year` |
| `year` | int | Yes | Year (2018-2025) |
| `district_id` | string | One of* | District |
| `geojson` | object | One of* | Custom area |
| `classifier` | string | No | `spectral` or `dynamic_world` |
| `baseline_year` | int | No | For change layers |
| `compare_year` | int | No | For year_to_year layer |

**Response:**
```json
{
  "tile_url": "https://earthengine.googleapis.com/map/.../{z}/{x}/{y}?token=...",
  "token": "abc123",
  "expires_at": "2024-01-15T11:30:00Z",
  "bounds": {"west": 77.2, "south": 12.8, "east": 77.8, "north": 13.3},
  "min_zoom": 8,
  "max_zoom": 16
}
```

---

## Trend Analysis

### POST /api/trend

Run trend statistics (Mann-Kendall, Sen's slope, Linear Regression).

**Request Body:**
```json
{
  "district_id": "bengaluru_urban",
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "season": {"name": "oct-dec"},
  "classifier": "spectral",
  "thresholds": {...},
  "variable": "vegetation"
}
```

**Variables:** `vegetation`, `water`, `built_bare`, `ndvi`, `mndwi`, `ndbi`

**Response:**
```json
{
  "variable": "vegetation",
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "values": [25.0, 25.5, 26.1, 25.8, 26.5, 26.2, 26.8, 27.1],
  "mann_kendall": {
    "tau": 0.643,
    "p_value": 0.012,
    "s": 18,
    "var_s": 28.7,
    "z": 2.51,
    "significant": true,
    "trend": "increasing"
  },
  "sen_slope": {
    "slope": 0.28,
    "intercept": -540.2,
    "ci_lower": 0.12,
    "ci_upper": 0.45,
    "confidence": 0.95
  },
  "linear_regression": {
    "slope": 0.29,
    "intercept": -556.4,
    "r_squared": 0.72,
    "p_value": 0.008,
    "ci_lower": 0.15,
    "ci_upper": 0.43,
    "significant": true
  },
  "interpretation": "Vegetation shows a significant increasing trend (p=0.0120, τ=0.643). Sen's slope: 0.2800/yr (95% CI: 0.1200 to 0.4500). Linear regression: slope=0.2900/yr (significant, p=0.0080, R²=0.720). WARNING: Only 8 data points (n=8). Statistical power is very low. Results should be interpreted with extreme caution.",
  "warnings": ["WARNING: Only 8 data points (n=8). Statistical power is very low..."]
}
```

---

## Accuracy Assessment

### POST /api/validate

Run accuracy assessment against WorldCover or user reference points.

**Request Body:**
```json
{
  "district_id": "bengaluru_urban",
  "year": 2020,
  "classifier": "spectral",
  "thresholds": {...},
  "reference_points_csv": "base64_encoded_csv"
}
```

**Response:**
```json
{
  "confusion_matrix": [
    [45, 2, 1, 0],
    [3, 240, 5, 2],
    [0, 4, 48, 1],
    [1, 0, 2, 47]
  ],
  "classes": ["water", "vegetation", "built_bare", "other"],
  "overall_accuracy": 0.92,
  "balanced_accuracy": 0.89,
  "producers_accuracy": {
    "water": 0.92,
    "vegetation": 0.96,
    "built_bare": 0.86,
    "other": 0.94
  },
  "users_accuracy": {
    "water": 0.94,
    "vegetation": 0.94,
    "built_bare": 0.91,
    "other": 0.94
  },
  "kappa": 0.88,
  "sample_size": 398,
  "reference_source": "WorldCover",
  "warnings": []
}
```

**Note:** WorldCover only available for 2020 (v100) and 2021 (v200). For other years, provide `reference_points_csv`.

---

## Transition Matrix

### POST /api/transitions

**Request Body:**
```json
{
  "district_id": "bengaluru_urban",
  "years": [2018, 2025],
  "season": {"name": "oct-dec"},
  "classifier": "spectral",
  "thresholds": {...}
}
```

**Response:**
```json
{
  "from_year": 2018,
  "to_year": 2025,
  "classes": ["water", "vegetation", "built_bare", "other"],
  "matrix_km2": [
    [9.5, 0.3, 0.2, 0.1],
    [0.4, 48.2, 1.2, 0.4],
    [0.1, 0.8, 38.5, 0.9],
    [0.0, 0.5, 0.3, 95.2]
  ],
  "matrix_pct": [
    [4.8, 0.2, 0.1, 0.1],
    [0.2, 24.1, 0.6, 0.2],
    [0.0, 0.4, 19.3, 0.5],
    [0.0, 0.3, 0.2, 47.6]
  ],
  "net_change_km2": {
    "water": 0.5,
    "vegetation": 5.2,
    "built_bare": 9.8,
    "other": -15.5
  }
}
```

---

## Landscape Metrics

### POST /api/landscape

**Response:**
```json
[
  {
    "year": 2018,
    "class": "vegetation",
    "patch_count": 1250,
    "mean_patch_size_km2": 0.042,
    "largest_patch_index": 15.3,
    "total_class_area_km2": 52.5
  }
]
```

---

## Urban Growth

### POST /api/urban-growth

**Response:**
```json
{
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "yearly_built_area_km2": {"2018": 40.3, "2019": 42.1, ...},
  "growth_rates": [
    {"year": 2019, "previous_year": 2018, "built_km2": 42.1, "previous_built_km2": 40.3, "absolute_change_km2": 1.8, "growth_rate_pct": 4.5}
  ],
  "expansion_direction": [
    {"sector": 0, "direction": "N", "angle_center": 11.25, "pixel_count": 1250},
    {"sector": 1, "direction": "NNE", "angle_center": 33.75, "pixel_count": 1100}
  ],
  "distance_profile_latest": [
    {"distance_km": 0.5, "built_area_km2": 2.1, "bin_start_km": 0, "bin_end_km": 1},
    {"distance_km": 1.5, "built_area_km2": 5.3, "bin_start_km": 1, "bin_end_km": 2}
  ],
  "yearly_distance_profiles": {...},
  "center_point": [77.59, 12.97]
}
```

---

## Environmental Context

### POST /api/environmental

**Response:**
```json
{
  "correlations": {
    "built_vs_lst": 0.65,
    "built_vs_ntl": 0.72,
    "built_vs_population": 0.81,
    "built_vs_rainfall": -0.23
  },
  "lst_trend": [{"year": 2018, "mean_lst_celsius": 28.5}, ...],
  "ntl_trend": [{"year": 2018, "mean_ntl_radiance": 12.3}, ...],
  "population_trend": [{"year": 2018, "total_population": 12500000}, ...],
  "rainfall_trend": [{"year": 2018, "annual_rainfall_mm": 920}, ...]
}
```

---

## Lakes

### POST /api/lakes

**Response:**
```json
{
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "yearly_stats": [
    {"year": 2018, "lake_count": 45, "total_lake_area_km2": 12.3, "lakes": [...]}
  ],
  "overall_change": {
    "year1_total_km2": 12.3,
    "year2_total_km2": 10.8,
    "total_change_km2": -1.5,
    "total_change_pct": -12.2
  },
  "flagged_lakes": [
    {"type": "overall", "message": "Total lake area decreased by 12.2% (1.50 km²)"}
  ],
  "summary": {
    "total_lakes_first_year": 45,
    "total_lakes_last_year": 42,
    "total_area_change_km2": -1.5,
    "total_area_change_pct": -12.2
  }
}
```

---

## Hotspots

### POST /api/hotspots

**Response:**
```json
{
  "from_year": 2018,
  "to_year": 2025,
  "cell_size_km": 1.0,
  "top_n": 20,
  "vegetation_loss": [
    {"cell_id": 123, "col": 5, "row": 12, "veg_loss_km2": 0.85, "geometry": {...}}
  ],
  "built_up_gain": [
    {"cell_id": 456, "col": 8, "row": 3, "built_gain_km2": 1.2, "geometry": {...}}
  ]
}
```

---

## PDF Report

### POST /api/report

Generate PDF report (not yet implemented).

---

## Error Responses

All errors follow RFC 7807:

```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
  "title": "Bad Request",
  "status": 400,
  "detail": "Year 2026 not in study period [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]",
  "instance": "/api/analysis"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (validation error)
- `404` - Not Found (job, district)
- `422` - Unprocessable Entity (GEE error)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `501` - Not Implemented
- `503` - Service Unavailable (GEE quota exceeded)

---

## WebSocket (Future)

Real-time progress updates for background jobs:
```
WS /api/ws/jobs/{job_id}
```