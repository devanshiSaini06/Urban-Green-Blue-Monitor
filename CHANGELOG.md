# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-17

### Added
- Complete backend API (FastAPI) with GEE processing pipeline
- React 18 + TypeScript frontend with Leaflet maps and Chart.js
- Google Earth Engine integration for Sentinel-2 and Dynamic World
- Spectral rule-based and Dynamic World land cover classification
- Mann-Kendall trend test, Sen's slope, linear regression
- WorldCover accuracy assessment (2020/2021)
- Land cover transition matrices
- Landscape metrics (patch count, size, LPI)
- Urban growth indicators (rate, rose diagram, distance profile)
- Environmental correlations (LST, NTL, population, rainfall)
- Lakes detection and shrinkage monitoring
- Change hotspots (1km grid)
- PDF report generation with ReportLab
- Shareable URLs with all view state
- CSV/Excel/GeoTIFF export
- Docker Compose for local development
- GitHub Actions CI/CD pipeline
- Comprehensive test suite (unit, integration, E2E)
- Static fallback HTML for Netlify/GitHub Pages

### Configuration
- Fixed study period: 2018–2025 (8 years)
- Seasonal windows: Oct–Dec (default), Jan–Mar, Mar–May, Jun–Sep
- Districts: Bengaluru Urban, Gautam Buddha Nagar
- GEE project: graphic-tide-513321-m3
- Analysis scale: 20m (selectable 10/20/30)
- Projection: EPSG:32643

### Classifiers
- Spectral rules (NDVI, MNDWI, NDBI thresholds adjustable)
- Dynamic World (mode of label band)

### Caveats
- 2018 data quality limited by Sentinel-2 coverage
- Spectral built-up class includes bare soil
- Single seasonal window effects
- District boundary dilution
- Low trend statistical power (n=8)
- WorldCover validation only 2020/2021

---

## [Unreleased]

### Planned
- Swipe comparison between years
- Time-lapse export (GIF/MP4)
- Custom polygon draw/upload
- Compare two custom areas
- Chat assistant (cached data only)
- Authentication (public read, admin write)
- 2030 projection (disabled by default)
- WebSocket real-time progress