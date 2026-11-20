# Urban Green and Blue Change Monitor

> Compare vegetation, surface water, and built-up/bare land changes in two Indian districts (2018–2025) using Sentinel-2 imagery processed in Google Earth Engine, presented in an interactive web dashboard.

## 🎯 Project Overview

This application monitors land cover change in:
- **Bengaluru Urban** (Karnataka)
- **Gautam Buddha Nagar** / Greater Noida (Uttar Pradesh)

Using Sentinel-2 surface reflectance (COPERNICUS/S2_SR_HARMONIZED) processed in Google Earth Engine with a fixed study period of **2018–2025** (8 years, Oct–Dec seasonal window).

## ✅ Feature Checklist

### Dashboard
- [x] **KPI Cards** - Vegetation, water, built-up change in km²/% with plain-language sentences
- [x] **Charts** - Area over time, share %, spectral indices, normalized (baseline=100), stacked composition, quality metrics
- [x] **Data Table** - Sortable, CSV/Excel export, quality flags
- [x] **Parameter Panel** - Year selector, season, classifier, thresholds, cloud limit, scale

### Maps
- [x] **Interactive Map** - Leaflet with all layers (true color, NDVI, MNDWI, NDBI, land cover, change)
- [x] **Year Slider** - Play/pause animation, opacity control
- [x] **District Boundary** - Toggleable outline
- [x] **Layer Controls** - Switch between 6 map layers
- [ ] Swipe comparison between years
- [ ] Time-lapse export (GIF/MP4)
- [ ] Draw polygon / upload GeoJSON/Shapefile
- [ ] Compare two custom areas

### Analysis
- [x] **Trend Statistics** - Mann-Kendall, Sen's slope, linear regression (with n=8 warning)
- [x] **Transition Matrix** - From-to class changes (placeholder UI)
- [x] **Landscape Metrics** - Patch count, mean patch size, LPI (placeholder UI)
- [x] **Urban Growth** - Growth rate, expansion direction, distance profile (placeholder UI)
- [x] **Environmental Context** - LST, NTL, population, rainfall correlations (placeholder UI)
- [x] **Accuracy Assessment** - WorldCover comparison (2020/2021 only)
- [x] **Sensitivity Analysis** - Threshold sliders with recomputation
- [ ] Projection to 2030 (statistical extrapolation)

### Operations
- [x] **Shareable URLs** - All view state encoded in URL
- [x] **PDF Report** - Generation endpoint (placeholder)
- [x] **Run History** - Metadata tracking
- [ ] Chat assistant (cached data only)
- [ ] Authentication (public read, admin write)

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│    Backend      │────▶│  Google Earth   │
│   (React +      │     │   (FastAPI)     │     │   Engine        │
│    Leaflet)     │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │                       ▼                       │
        │              ┌─────────────────┐              │
        │              │    Cache        │              │
        │              │   (SQLite/      │              │
        │              │   Cloud Storage)│              │
        │              └─────────────────┘              │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Firebase       │     │  Cloud Run      │     │  Secret Manager │
│  Hosting        │     │  (Backend)      │     │  (GEE Key)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Google Cloud SDK (`gcloud`) with GEE access
- GEE service account key (JSON)

### 1. Clone and Configure

```bash
git clone <repository>
cd urban-green-blue-monitor

# Copy environment template
cp .env.example .env

# Edit .env with your values:
# - GEE_SERVICE_ACCOUNT_KEY_PATH=/path/to/your/gee-key.json
# - Or set GEE_SERVICE_ACCOUNT_KEY_JSON (base64 encoded)
```

### 2. Prepare GEE Credentials

```bash
# Option A: Use service account key file (for Docker)
mkdir -p ~/.config/gcloud
cp /path/to/your/gee-service-account.json ~/.config/gcloud/gee-key.json

# Option B: Use gcloud auth (for local development without Docker)
gcloud auth application-default login
```

### 3. Start Services

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 4. Run Analysis

1. Open http://localhost:5173
2. Select a district (Bengaluru Urban or Gautam Buddha Nagar)
3. Select years (e.g., 2018 and 2025)
4. Click "Run Analysis"
5. View results in Dashboard, Map, and Analysis tabs

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEE_PROJECT_ID` | GEE Cloud project ID | `graphic-tide-513321-m3` |
| `GEE_SERVICE_ACCOUNT_KEY_PATH` | Path to service account JSON | - |
| `GEE_SERVICE_ACCOUNT_KEY_JSON` | Base64 encoded service account JSON | - |
| `API_HOST` | Backend host | `0.0.0.0` |
| `API_PORT` | Backend port | `8000` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173` |
| `CACHE_DIR` | Cache directory | `./cache` |
| `CACHE_TTL_DAYS` | Cache TTL | `30` |

### Study Period Configuration

The study years are defined in `backend/config.py`:

```python
STUDY_YEARS: List[int] = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
```

To extend: modify this single list.

### Seasonal Windows

```python
SEASON_WINDOWS: Dict[str, tuple] = {
    "oct-dec": (10, 1),    # Oct 1 - Dec 31
    "jan-mar": (1, 4),     # Jan 1 - Mar 31
    "mar-may": (3, 6),     # Mar 1 - May 31
    "jun-sep": (6, 10),    # Jun 1 - Sep 30
}
```

### Classification Thresholds (all adjustable in UI)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mndwi_water` | 0.10 | MNDWI > threshold = water |
| `ndvi_water_max` | 0.15 | NDVI < threshold for water |
| `ndvi_veg_min` | 0.35 | NDVI ≥ threshold = vegetation |
| `ndbi_built_min` | 0.0 | NDBI > threshold = built-up |
| `ndvi_built_max` | 0.20 | NDVI < threshold for built-up |

## 📊 Methodology

### Data Processing Pipeline

1. **Collection**: Sentinel-2 SR Harmonized, filtered to district + date window, cloud % < 80
2. **Cloud Mask**: SCL band classes 0,1,3,8,9,10,11 masked out
3. **Bands**: B2, B3, B4, B8, B11, B12 × 0.0001
4. **Composite**: Median of masked images, clipped to district
5. **Indices**: NDVI, NDWI, MNDWI, NDBI
6. **Classification**: Spectral rules OR Dynamic World (mode of label)
7. **Area Calc**: Pixel area (km²), percentages use valid (unmasked) area

### Spectral Classification Rules

| Class | Rule |
|-------|------|
| Water | MNDWI > 0.10 AND NDVI < 0.15 |
| Vegetation | NDVI ≥ 0.35 AND NOT water |
| Built-up/Bare | NDBI > 0 AND NDVI < 0.20 AND NOT water |
| Other | Valid pixels not classified above |

### Dynamic World Mapping

| DW Class | Our Class |
|----------|-----------|
| water (0) | water |
| trees (1), grass (2), flooded_veg (3), crops (4), shrub (5) | vegetation |
| built (6), bare (7) | built_bare |
| snow (8) | other |

## 🧪 Testing

### Backend Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Frontend Tests

```bash
cd frontend
npm install
npm run test
```

### E2E Tests

```bash
cd frontend
npm run test:e2e  # Requires Playwright
```

## 🐳 Deployment

### Local Production Build

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

### Google Cloud Deployment

#### Backend (Cloud Run)

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/ugbcm-backend ./backend

# Deploy
gcloud run deploy ugbcm-backend \
  --image gcr.io/PROJECT_ID/ugbcm-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEE_PROJECT_ID=graphic-tide-513321-m3 \
  --set-secrets GEE_SERVICE_ACCOUNT_KEY_JSON=gee-key:latest
```

#### Frontend (Firebase Hosting)

```bash
cd frontend
npm run build
firebase deploy --only hosting
```

#### Secrets (Secret Manager)

```bash
# Store GEE service account key
echo -n '{"type": "service_account", ...}' | gcloud secrets create gee-key --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding gee-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Cost Estimate (Monthly)

| Service | Estimated Cost |
|---------|----------------|
| Cloud Run (backend) | $5-20 |
| Firebase Hosting | Free tier |
| Cloud Storage (cache) | $1-5 |
| Secret Manager | $0.06/secret |
| GEE Computation | Free (within limits) |
| **Total** | **~$10-30/month** |

Set budget alerts in GCP Console → Billing → Budgets.

## 📓 Notebooks

- `notebooks/reproduce_headline_stats.ipynb` - Reproduce key statistics without web app
- `notebooks/explore_data.ipynb` - Interactive data exploration

## 📜 GEE Scripts

- `gee_scripts/headline_stats.js` - GEE Code Editor script for headline numbers
- `gee_scripts/full_pipeline.js` - Complete processing pipeline

## 📚 Documentation

- `docs/methodology.md` - Academic methodology document
- `docs/api.md` - API reference
- `docs/deployment.md` - Detailed deployment guide
- `docs/caveats.md` - Top 10 caveats and limitations

## ⚠️ Top 10 Caveats

1. **2018 Data Quality** - Sentinel-2 SR coverage over India was thinner in 2018; expect fewer images and lower coverage
2. **Spectral Built-up Ambiguity** - NDBI-based built-up class captures bare/fallow soil; crop cycles cause false changes
3. **Seasonal Window Effects** - Oct-Dec mixes post-monsoon water and crop residues; compare with other seasons
4. **District Boundary Dilution** - Large farmland/forest at edges dilutes urban change signal
5. **Low Statistical Power** - n=8 years gives very low power for trend tests; "significant" may be spurious
6. **WorldCover Reference Limited** - Only 2020 (v100) and 2021 (v200) available for validation
7. **Dynamic World Temporal Resolution** - Annual mode may miss sub-annual dynamics
8. **Cloud Mask Imperfections** - SCL-based masking may miss thin clouds or over-mask
9. **Scale Dependency** - 20m analysis scale misses fine-grained changes; 10m available but slower
10. **Projection Distortion** - EPSG:32643 (UTM 43N) suitable for India but verify for other regions

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## 📞 Support

For issues, please open a GitHub issue or contact the maintainers.