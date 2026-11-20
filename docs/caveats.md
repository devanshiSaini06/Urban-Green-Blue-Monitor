# Top 10 Caveats and Limitations

This document lists the most important caveats for interpreting results from the Urban Green and Blue Change Monitor. **Every user should read this before drawing conclusions.**

---

## 1. 2018 Data Quality — Sentinel-2 Coverage Was Thinner

**Issue**: Sentinel-2 surface reflectance (L2A) collection over India had significantly fewer acquisitions in 2018 compared to later years.

**Impact**:
- Fewer images in 2018 composites (often < 5 vs. 15+ in 2020+)
- Lower valid pixel coverage due to clouds/gaps
- Higher uncertainty in 2018 baseline values
- Apparent "large changes" 2018→2019 may be artifacts

**Mitigation**:
- UI shows image count and coverage % per year
- Quality flags warn when images < 5 or coverage < 50%
- Recommended baseline year defaults to best-quality year (usually 2020 or later)
- **Do not use 2018 as baseline without acknowledging this limitation**

---

## 2. Spectral "Built-up" Class Includes Bare Soil

**Issue**: The NDBI-based built-up rule (NDBI > 0, NDVI < 0.2) cannot distinguish impervious surfaces from bare soil, fallow fields, or construction sites.

**Impact**:
- Crop harvest cycles cause apparent "built-up gain/loss"
- Fallow agricultural land classified as built-up
- Dry season bare soil inflates built-up area
- Monsoon season vegetation masks built-up

**Mitigation**:
- **Always compare with Dynamic World classifier** (separates built vs. bare)
- Use seasonal windows consistently
- Check NDVI time series at suspicious locations
- Urban growth indicators use latest year only (less affected)

---

## 3. Single Seasonal Window (Oct–Dec) Mixes Signals

**Issue**: The default Oct–Dec window captures:
- Post-monsoon surface water (tanks, lakes full)
- Post-kharif crop residues (vegetation signal)
- Early rabi crop emergence

**Impact**:
- Water area varies with monsoon rainfall
- Vegetation signal confounds crops vs. natural vegetation
- Year-to-year rainfall differences create false "change"

**Mitigation**:
- Compare multiple seasonal windows (Jan–Mar, Mar–May, Jun–Sep)
- Use environmental context (rainfall correlation)
- Dynamic World has better crop/natural vegetation separation
- UI warns when comparing years with different windows

---

## 4. District Boundaries Include Rural/Forest Areas

**Issue**: District boundaries encompass large farmland, forest, and water bodies at edges, not just urban areas.

**Impact**:
- Urban change signal diluted by stable rural classes
- Percent changes appear smaller than reality
- Built-up growth rate reflects district-scale, not city-scale

**Mitigation**:
- Draw custom polygon around urban area (feature 6)
- Upload GeoJSON of municipal boundary
- Use hotspot module to find urban change concentrations
- Distance-from-center profile isolates urban core

---

## 5. Trend Analysis: n = 8 Has Very Low Statistical Power

**Issue**: Mann-Kendall, Sen's slope, and linear regression with only 8 data points.

**Statistical Reality**:
- Minimum n for reasonable MK power: ~10–15
- With n=8, only very strong monotonic trends (τ > 0.7) reach p < 0.05
- False negative rate is high; false positive rate inflated by autocorrelation
- Sen's slope CI is extremely wide

**UI Warning**: Every trend result shows:
> "WARNING: Only 8 data points (n=8). Statistical power is very low. Results should be interpreted with extreme caution."

**Recommendation**: Treat trend results as **exploratory only**. Do not cite as evidence of significant change.

---

## 6. WorldCover Validation Only for 2020 and 2021

**Issue**: ESA WorldCover reference data exists only for 2020 (v100) and 2021 (v200).

**Impact**:
- No independent validation for 2018, 2019, 2022, 2023, 2024, 2025
- Accuracy metrics only reflect those two years
- Classifier performance may differ in other years

**Mitigation**:
- Upload custom reference points for other years
- Use Dynamic World as secondary reference (though also model-derived)
- Report validation year explicitly in any publication

---

## 7. Cloud Mask Imperfections

**Issue**: SCL-based cloud masking has known limitations:
- Thin cirrus (class 10) sometimes missed
- Cloud shadows (class 3) not always adjacent to clouds
- Bright surfaces (sand, rooftops) occasionally misclassified as cloud
- Snow/ice (class 11) masked even when not present

**Impact**:
- Residual clouds bias indices (especially NDVI, NDBI)
- Over-masking reduces valid pixel count
- Snow masking irrelevant for study area but reduces coverage

**Mitigation**:
- Cloud threshold < 80% filters worst images
- Median composite reduces outlier influence
- Quality flags show coverage %

---

## 8. Scale Dependency (20 m Default)

**Issue**: 20 m analysis scale (driven by SWIR bands) misses:
- Narrow linear features (roads, canals)
- Small water bodies (< 0.04 km²)
- Fragmented vegetation patches
- Individual buildings

**Impact**:
- Patch metrics biased (fewer, larger patches)
- Urban growth underestimates infill development
- Lake detection misses small ponds

**Mitigation**:
- 10 m scale available (uses only 10 m bands, no SWIR indices)
- 30 m scale for faster regional overview
- Report scale used in all outputs

---

## 9. Dynamic World Temporal Resolution

**Issue**: Dynamic World provides predictions every ~5 days, but:
- Annual mode composites may smooth seasonal dynamics
- Label confidence not exposed in mode reducer
- Model trained on 2017–2021 data; extrapolation to 2025 uncertain

**Impact**:
- May miss rapid changes (floods, construction)
- Class stability over time not guaranteed
- "Built" class includes both impervious and bare in some versions

**Mitigation**:
- Use spectral classifier for sub-annual detail
- Compare both classifiers side-by-side
- Note Dynamic World version in metadata

---

## 10. Projection and Geometric Distortion

**Issue**: EPSG:32643 (UTM Zone 43N) is appropriate for study area but:
- District boundaries span ~0.5° longitude (within zone)
- Area calculations in UTM are accurate at this scale
- Web maps use Web Mercator (EPSG:3857) causing visual distortion

**Impact**:
- km² values from GEE (UTM) are correct
- Web map display areas visually distorted at edges
- Tile URLs use Web Mercator projection

**Mitigation**:
- Trust GEE-computed areas (EPSG:32643)
- Web map for visualization only
- Export GeoTIFF for precise measurements

---

## Summary Table

| Caveat | Severity | Affects | Workaround |
|--------|----------|---------|------------|
| 2018 data quality | High | Baseline, trends | Use 2020+ baseline |
| Built-up = bare soil | High | Built-up area, trends | Use Dynamic World |
| Seasonal window | Medium | Water, vegetation | Compare seasons |
| Boundary dilution | Medium | Urban change % | Custom polygons |
| Low trend power | High | Trend significance | Exploratory only |
| Limited validation | Medium | Accuracy claims | Upload reference points |
| Cloud mask | Low-Medium | All indices | Quality flags |
| Scale dependency | Medium | Fine features | 10 m option |
| DW temporal limits | Low | Dynamic World | Spectral for detail |
| Projection | Low | Web display | Export GeoTIFF |

---

## Best Practices for Reporting

1. **Always state**: study period, seasonal window, classifier, thresholds, scale
2. **Report quality flags** for key years (especially baseline)
3. **Show both classifiers** for built-up changes
4. **Qualify trend statements**: "exploratory trend analysis with n=8 suggests..."
5. **Include caveats** in any publication or report
6. **Share the URL** — it encodes all parameters for reproducibility

---

*This document should be updated as new limitations are discovered or methods improve.*