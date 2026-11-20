# Methodology Document

## Urban Green and Blue Change Monitor: Land Cover Change Analysis in Indian Districts (2018–2025)

---

## 1. Introduction

This document describes the methodology for the **Urban Green and Blue Change Monitor**, a system for quantifying and visualizing changes in vegetation, surface water, and built-up/bare land in two Indian districts—Bengaluru Urban (Karnataka) and Gautam Buddha Nagar (Uttar Pradesh, containing Greater Noida)—between 2018 and 2025 using Sentinel-2 satellite imagery processed in Google Earth Engine (GEE).

---

## 2. Study Area

### 2.1 Districts

| District | State | GEE Asset | Feature Index |
|----------|-------|-----------|---------------|
| Bengaluru Urban | Karnataka | `projects/graphic-tide-513321-m3/assets/Bengaluru` | 1 |
| Gautam Buddha Nagar | Uttar Pradesh | `projects/graphic-tide-513321-m3/assets/GautamBuddhaNagar` | 0 |

### 2.2 Boundary Data

District boundaries are stored as FeatureCollections in GEE assets. The specified feature index selects the correct polygon from each collection. Boundaries are simplified to ~50 m for web display.

---

## 3. Data Sources

### 3.1 Primary: Sentinel-2 Surface Reflectance

- **Collection**: `COPERNICUS/S2_SR_HARMONIZED`
- **Bands Used**: B2 (Blue), B3 (Green), B4 (Red), B8 (NIR), B11 (SWIR1), B12 (SWIR2), SCL (Scene Classification)
- **Scale Factor**: 0.0001 (to convert DN to reflectance)
- **Temporal Resolution**: 5 days (dual satellite)
- **Spatial Resolution**: 10 m (visible/NIR), 20 m (SWIR)

### 3.2 Secondary: Google Dynamic World

- **Collection**: `GOOGLE/DYNAMICWORLD/V1`
- **Band**: `label` (land cover classification, 10 classes)
- **Resolution**: 10 m
- **Temporal Coverage**: 2017–present

### 3.3 Validation: ESA WorldCover

- **2020**: `ESA/WorldCover/v100`
- **2021**: `ESA/WorldCover/v200`
- **Resolution**: 10 m
- **Classes**: 11 land cover classes

### 3.4 Environmental Context (Optional)

| Dataset | Collection | Resolution | Variables |
|---------|------------|------------|-----------|
| Landsat LST | `LANDSAT/LC08/C02/T1_L2`, `LANDSAT/LC09/C02/T1_L2` | ~1000 m | Land Surface Temperature |
| VIIRS Night Lights | `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` | ~500 m | Night-time radiance |
| WorldPop | `WorldPop/GP/100m/pop` | ~100 m | Population count |
| CHIRPS | `UCSB-CHG/CHIRPS/DAILY` | ~5 km | Daily precipitation |

---

## 4. Temporal Framework

### 4.1 Study Period

**Fixed**: 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 (8 years)

### 4.2 Seasonal Windows

Default: **October 1 – December 31** (post-monsoon, dry season in peninsular India)

Alternative windows (selectable):
- Jan–Mar (winter)
- Mar–May (pre-monsoon)
- Jun–Sep (monsoon)
- Custom date range

### 4.3 Annual Composite

For each year and season: median of all cloud-masked images within the date window.

---

## 5. Preprocessing

### 5.1 Cloud Masking

Using the SCL (Scene Classification) band from Sentinel-2 L2A:
- **Masked classes**: 0 (no data), 1 (saturated/defective), 3 (cloud shadows), 8 (cloud medium probability), 9 (cloud high probability), 10 (thin cirrus), 11 (snow/ice)
- **Retained classes**: 2 (dark area), 4 (vegetation), 5 (bare soil), 6 (water), 7 (cloud low probability)

### 5.2 Band Selection & Scaling

| Band | Central λ (nm) | Use |
|------|----------------|-----|
| B2 | 490 | Blue (true color) |
| B3 | 560 | Green (true color, NDWI, MNDWI) |
| B4 | 665 | Red (true color, NDVI) |
| B8 | 842 | NIR (NDVI, NDWI, NDBI) |
| B11 | 1610 | SWIR1 (MNDWI, NDBI) |
| B12 | 2190 | SWIR2 |

All bands multiplied by **0.0001** to convert to reflectance (0–1).

### 5.3 Spatial Parameters

- **Analysis Scale**: 20 m (selectable: 10, 20, 30 m)
- **Projection**: EPSG:32643 (UTM Zone 43N)
- **Clipping**: All composites clipped to district boundary

---

## 6. Spectral Indices

| Index | Formula | Range | Interpretation |
|-------|---------|-------|----------------|
| **NDVI** | (B8 - B4) / (B8 + B4) | [-1, 1] | Vegetation greenness |
| **NDWI** | (B3 - B8) / (B3 + B8) | [-1, 1] | Water content (Gao 1996) |
| **MNDWI** | (B3 - B11) / (B3 + B11) | [-1, 1] | Enhanced water (Xu 2006) |
| **NDBI** | (B11 - B8) / (B11 + B8) | [-1, 1] | Built-up/bare soil (Zha et al. 2003) |

---

## 7. Land Cover Classification

### 7.1 Spectral Rule-Based Classifier (Default)

Hierarchical decision rules (all thresholds adjustable):

| Class | Rule | Default Thresholds |
|-------|------|-------------------|
| **Water** | MNDWI > τ₁ AND NDVI < τ₂ | τ₁ = 0.10, τ₂ = 0.15 |
| **Vegetation** | NDVI ≥ τ₃ AND NOT water | τ₃ = 0.35 |
| **Built-up/Bare** | NDBI > τ₄ AND NDVI < τ₅ AND NOT water | τ₄ = 0.0, τ₅ = 0.20 |
| **Other** | Valid pixels not classified above | — |

**Note**: The built-up class based on NDBI also captures bare soil, fallow fields, and impervious surfaces. This is a known limitation (see Caveats).

### 7.2 Dynamic World Classifier (Alternative)

Uses the mode of the `label` band over the seasonal window. Remapping:

| DW Class | Our Class |
|----------|-----------|
| 0: water | water |
| 1: trees, 2: grass, 3: flooded vegetation, 4: crops, 5: shrub/scrub | vegetation |
| 6: built, 7: bare | built_bare |
| 8: snow | other |

---

## 8. Area Calculation

### 8.1 Pixel Area

`ee.Image.pixelArea()` returns area in m² per pixel. Converted to km² (÷ 10⁶).

### 8.2 Class Areas

For each class: sum of pixel areas where classification == class.

### 8.3 Percentages

Denominator = **total valid (unmasked) area** within district boundary.
Also reported: raw district area (including masked pixels).

### 8.4 Reported Metrics (per district, per year)

- Images used in composite
- Valid area (km²)
- Vegetation area (km²) and %
- Water area (km²) and %
- Built-up/bare area (km²) and %
- Other area (km²) and %
- Mean NDVI, MNDWI, NDBI (over valid pixels)
- Composite first/last image dates

---

## 9. Quality Assurance

### 9.1 Outlier Detection

Flag years where vegetation % differs from the average of neighboring years by > 25% (configurable).

### 9.2 Low-Quality Flags

- **Low image count**: < 5 images in composite (configurable)
- **Low coverage**: Valid area < 50% of district (configurable)
- **Outlier**: As above

### 9.3 Baseline Year Recommendation

Automatic recommendation based on quality score:
- No low-image warning: +2
- No low-coverage warning: +2
- No outlier flag: +1
Highest score = recommended baseline.

---

## 10. Change Analysis

### 10.1 Pairwise Change

For any two years: absolute and percentage change per class.

### 10.2 Transition Matrix

From-to class transitions (km² and %) between two years.

### 10.3 Trend Analysis (8 years)

| Method | Implementation | Output |
|--------|----------------|--------|
| **Mann-Kendall** | Pure Python, tie-corrected | τ, p-value, trend direction |
| **Sen's Slope** | Theil-Sen estimator with CI | Slope (units/yr), 95% CI |
| **Linear Regression** | OLS with normal-approx CI | Slope, R², p-value, 95% CI |

**Critical Warning**: n = 8 provides **very low statistical power**. All "significant" results must be interpreted with extreme caution. The UI displays an explicit warning.

---

## 11. Accuracy Assessment

### 11.1 Reference Data

- **WorldCover 2020 (v100)** and **2021 (v200)** only
- Remapped to 4 classes (see Section 7.2)

### 11.2 Sampling Design

- **Stratified**: 300 points per reference class (1200 total)
- **Random**: ~1500 points across all classes
- **Total**: ~2700 points per assessment

### 11.3 Metrics

- Confusion matrix (4×4)
- Overall accuracy
- Balanced accuracy (mean per-class recall)
- Producer's accuracy (recall) per class
- User's accuracy (precision) per class
- Cohen's Kappa

### 11.4 User Uploads

Users may provide custom reference points CSV (columns: lat, lon, reference_class) for any year.

---

## 12. Advanced Analyses

### 12.1 Landscape Metrics (Vegetation)

Using `reduceToVectors` (8-connected):
- Patch count
- Mean patch size (km²)
- Largest Patch Index (%)

### 12.2 Urban Growth Indicators

- Yearly built-up growth rate (% and km²)
- Expansion direction: 16-sector rose diagram from district centroid
- Distance-from-center profile: built-up area in 1 km concentric rings

### 12.3 Lakes Module

- Detect water bodies per year (connected components)
- Rank by area change
- Flag lakes shrinking > configurable threshold
- Accept user-uploaded named lakes layer (GeoJSON)

### 12.4 Hotspot Module

- 1 km grid over district
- Rank cells by vegetation loss and built-up gain
- Export top N hotspots

### 12.4 Environmental Correlations (Optional)

Pearson correlations between built-up area and:
- Landsat LST (annual mean)
- VIIRS NTL (annual mean)
- WorldPop population (annual)
- CHIRPS rainfall (annual sum)

---

## 13. Sensitivity Analysis

Interactive threshold sliders (NDVI, MNDWI, NDBI) with:
- Real-time recomputation (debounced)
- Chart showing headline change vs. threshold value
- Default ±0.1 range around current value

---

## 14. Limitations & Caveats

See `docs/caveats.md` for the complete list of 10 key caveats.

Key limitations:
1. 2018 data quality issues
2. Spectral built-up ≠ impervious surface
3. Single seasonal window effects
4. District boundary dilution
5. Low trend statistical power (n=8)
6. WorldCover reference only 2020/2021
7. Cloud mask imperfections
8. Scale dependency (20m default)
9. Dynamic World temporal resolution
10. Projection constraints

---

## 15. References

### Satellite Data
- Sentinel-2: Drusch et al. (2012), "Sentinel-2: ESA's Optical High-Resolution Mission for GMES Operational Services"
- Dynamic World: Brown et al. (2022), "Dynamic World, Near real-time global 10 m land use land cover"
- WorldCover: Zanaga et al. (2021), "ESA WorldCover 10 m 2020 v100"

### Indices
- NDVI: Rouse et al. (1974), "Monitoring vegetation systems in the Great Plains with ERTS"
- NDWI: Gao (1996), "NDWI—A normalized difference water index for remote sensing of vegetation liquid water from space"
- MNDWI: Xu (2006), "Modification of normalised difference water index (NDWI) to enhance open water features"
- NDBI: Zha et al. (2003), "Use of normalized difference built-up index in automatically mapping urban areas from TM imagery"

### Trend Analysis
- Mann (1945), "Nonparametric tests against trend"
- Kendall (1975), "Rank Correlation Methods"
- Sen (1968), "Estimates of the regression coefficient based on Kendall's tau"
- Hirsch et al. (1982), "A comparison of trend test methods"

### Accuracy Assessment
- Congalton & Green (2009), "Assessing the Accuracy of Remotely Sensed Data"
- Olofsson et al. (2014), "Good practices for estimating area and assessing accuracy of land change"

---

## 16. Software Versions

- Python: 3.11
- Earth Engine API: 0.1.384
- FastAPI: 0.109
- React: 18.2
- Leaflet: 1.9.4
- Chart.js: 4.4

---

*Document version: 1.0 | Date: 2024 | Author: Urban Green and Blue Change Monitor Team*