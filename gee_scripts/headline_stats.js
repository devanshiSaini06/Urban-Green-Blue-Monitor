/**
 * Urban Green and Blue Change Monitor - Headline Statistics
 * GEE Code Editor Script
 *
 * Run this in the Google Earth Engine Code Editor (code.earthengine.google.com)
 * to reproduce the headline numbers for both districts.
 *
 * Requirements:
 * - GEE project: graphic-tide-513321-m3
 * - Assets: projects/graphic-tide-513321-m3/assets/Bengaluru (feature 1)
 *           projects/graphic-tide-513321-m3/assets/GautamBuddhaNagar (feature 0)
 */

// =============================================================================
// CONFIGURATION
// =============================================================================
var PROJECT_ID = 'graphic-tide-513321-m3';
var STUDY_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];
var SEASON = 'oct-dec';  // Oct 1 - Dec 31
var SCALE = 20;
var CLOUD_THRESHOLD = 80;
var EXPORT_CRS = 'EPSG:32643';

// Classification thresholds (adjustable)
var THRESHOLDS = {
  mndwi_water: 0.10,
  ndvi_water_max: 0.15,
  ndvi_veg_min: 0.35,
  ndbi_built_min: 0.0,
  ndvi_built_max: 0.20
};

// District assets
var DISTRICTS = {
  bengaluru_urban: {
    asset_id: 'projects/graphic-tide-513321-m3/assets/Bengaluru',
    feature_index: 1,
    name: 'Bengaluru Urban'
  },
  gautam_buddha_nagar: {
    asset_id: 'projects/graphic-tide-513321-m3/assets/GautamBuddhaNagar',
    feature_index: 0,
    name: 'Gautam Buddha Nagar'
  }
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/** Get district geometry from asset */
function getDistrictGeometry(districtKey) {
  var district = DISTRICTS[districtKey];
  var fc = ee.FeatureCollection(district.asset_id);
  var feature = fc.toList(fc.size()).get(district.feature_index);
  return ee.Feature(feature).geometry();
}

/** Get season dates */
function getSeasonDates(year, season) {
  if (season === 'oct-dec') {
    return [ee.Date.fromYMD(year, 10, 1), ee.Date.fromYMD(year + 1, 1, 1)];
  } else if (season === 'jan-mar') {
    return [ee.Date.fromYMD(year, 1, 1), ee.Date.fromYMD(year, 4, 1)];
  } else if (season === 'mar-may') {
    return [ee.Date.fromYMD(year, 3, 1), ee.Date.fromYMD(year, 6, 1)];
  } else if (season === 'jun-sep') {
    return [ee.Date.fromYMD(year, 6, 1), ee.Date.fromYMD(year, 10, 1)];
  }
  throw 'Unknown season: ' + season;
}

/** Cloud mask using SCL band */
function maskSentinel2Clouds(image) {
  var scl = image.select('SCL');
  var mask = scl.neq(0).and(scl.neq(1)).and(scl.neq(3))
      .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return image.updateMask(mask)
      .select(['B2','B3','B4','B8','B11','B12'])
      .multiply(0.0001)
      .copyProperties(image, ['system:time_start', 'system:index_id', 'CLOUDY_PIXEL_PERCENTAGE']);
}

/** Compute spectral indices */
function computeIndices(image) {
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');
  var mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  var ndbi = image.normalizedDifference(['B11', 'B8']).rename('NDBI');
  return image.addBands([ndvi, ndwi, mndwi, ndbi]);
}

/** Spectral rule-based classification */
function classifySpectral(image, thresholds) {
  var ndvi = image.select('NDVI');
  var mndwi = image.select('MNDWI');
  var ndbi = image.select('NDBI');

  var water = mndwi.gt(thresholds.mndwi_water).and(ndvi.lt(thresholds.ndvi_water_max));
  var vegetation = ndvi.gte(thresholds.ndvi_veg_min).and(water.not());
  var built_bare = ndbi.gt(thresholds.ndbi_built_min)
      .and(ndvi.lt(thresholds.ndvi_built_max)).and(water.not());
  var valid_mask = ndvi.mask();
  var other = valid_mask.and(water.not()).and(vegetation.not()).and(built_bare.not());

  var classification = water.multiply(1)
      .add(vegetation.multiply(2))
      .add(built_bare.multiply(3))
      .add(other.multiply(4))
      .rename('landcover').byte();
  return image.addBands(classification);
}

/** Dynamic World classification */
function classifyDynamicWorld(geometry, startDate, endDate) {
  var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
      .filterBounds(geometry)
      .filterDate(startDate, endDate)
      .select('label')
      .mode()
      .rename('landcover');

  // Remap DW classes to our 4 classes
  // 0:water, 1:trees, 2:grass, 3:flooded_veg, 4:crops, 5:shrub, 6:built, 7:bare, 8:snow
  var remap = ee.Image.constant([
    [0, 1],   // water -> 1
    [1, 2],   // trees -> 2
    [2, 2],   // grass -> 2
    [3, 1],   // flooded_veg -> 1
    [4, 2],   // crops -> 2
    [5, 2],   // shrub -> 2
    [6, 3],   // built -> 3
    [7, 3],   // bare -> 3
    [8, 4],   // snow -> 4
  ]);
  return dw.remap(remap.slice(1, 0), remap.slice(1, 1), 4, 'landcover').byte();
}

/** Compute area statistics */
function computeAreas(classification, geometry, scale, rawAreaKm2) {
  var pixelArea = ee.Image.pixelArea().divide(1e6); // km²
  var classWithArea = classification.addBands(pixelArea.rename('area_km2'));

  var stats = classWithArea.reduceRegion({
    reducer: ee.Reducer.sum().group({groupField: 0, groupName: 'class'}),
    geometry: geometry,
    scale: scale,
    maxPixels: 1e13,
    bestEffort: true,
    crs: EXPORT_CRS
  });

  var validArea = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: geometry,
    scale: scale,
    maxPixels: 1e13,
    bestEffort: true,
    crs: EXPORT_CRS
  }).get('area_km2');

  var groups = ee.List(stats.get('groups'));
  var validKm2 = ee.Number(validArea);

  // Parse groups into class areas
  var classAreas = groups.map(function(group) {
    group = ee.Dictionary(group);
    var classId = ee.Number(group.get('class')).int();
    var area = ee.Number(group.get('sum'));
    return ee.Feature(null, {class: classId, area: area});
  });

  return {
    classAreas: classAreas,
    validKm2: validKm2,
    rawAreaKm2: rawAreaKm2
  };
}

/** Compute mean indices */
function computeMeanIndices(composite, geometry, scale) {
  return composite.select(['NDVI', 'MNDWI', 'NDBI']).reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: geometry,
    scale: scale,
    maxPixels: 1e13,
    bestEffort: true,
    crs: EXPORT_CRS
  });
}

/** Run analysis for a single year */
function analyzeYear(districtKey, year, classifier) {
  var district = DISTRICTS[districtKey];
  var geometry = getDistrictGeometry(districtKey);
  var dates = getSeasonDates(year, SEASON);
  var startDate = dates[0];
  var endDate = dates[1];

  var rawAreaKm2 = geometry.area(1).divide(1e6);

  if (classifier === 'spectral') {
    var collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(geometry)
        .filterDate(startDate, endDate)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_THRESHOLD))
        .map(maskSentinel2Clouds);

    var imagesUsed = collection.size();
    var composite = collection.median().clip(geometry);
    composite = computeIndices(composite);
    composite = classifySpectral(composite, THRESHOLDS);

    // Get composite dates
    var dateList = collection.aggregate_array('system:time_start');
    var firstDate = ee.Date(dateList.sort().get(0)).format('YYYY-MM-dd');
    var lastDate = ee.Date(dateList.sort().get(dateList.size().subtract(1))).format('YYYY-MM-dd');

    return {
      year: year,
      classifier: 'spectral',
      imagesUsed: imagesUsed,
      composite: composite,
      firstDate: firstDate,
      lastDate: lastDate,
      geometry: geometry,
      rawAreaKm2: rawAreaKm2
    };
  } else {
    var composite = classifyDynamicWorld(geometry, startDate, endDate);
    return {
      year: year,
      classifier: 'dynamic_world',
      imagesUsed: ee.Number(1),
      composite: composite,
      firstDate: startDate.format('YYYY-MM-dd'),
      lastDate: endDate.format('YYYY-MM-dd'),
      geometry: geometry,
      rawAreaKm2: rawAreaKm2
    };
  }
}

// =============================================================================
// MAIN ANALYSIS
// =============================================================================

// Run for both districts with both classifiers
var results = {};

Object.keys(DISTRICTS).forEach(function(districtKey) {
  var district = DISTRICTS[districtKey];
  print('\\n========== ' + district.name + ' ==========');

  ['spectral', 'dynamic_world'].forEach(function(classifier) {
    print('\\n--- ' + classifier.toUpperCase() + ' ---');

    var yearlyResults = STUDY_YEARS.map(function(year) {
      var result = analyzeYear(districtKey, year, classifier);

      // Compute areas
      var areas = computeAreas(
          result.composite.select('landcover'),
          result.geometry,
          SCALE,
          result.rawAreaKm2
      );

      // Compute mean indices (spectral only)
      var means = classifier === 'spectral'
          ? computeMeanIndices(result.composite, result.geometry, SCALE)
          : {NDVI: 0, MNDWI: 0, NDBI: 0};

      // Print summary
      var validKm2 = areas.validKm2;
      var vegArea = ee.Number(areas.classAreas.filter(ee.Filter.eq('class', 2)).first().get('area'));
      var waterArea = ee.Number(areas.classAreas.filter(ee.Filter.eq('class', 1)).first().get('area'));
      var builtArea = ee.Number(areas.classAreas.filter(ee.Filter.eq('class', 3)).first().get('area'));

      print('Year ' + year + ': images=' + result.imagesUsed.getInfo() +
          ', valid=' + validKm2.getInfo().toFixed(2) + ' km²' +
          ', veg=' + vegArea.getInfo().toFixed(2) + ' km²' +
          ', water=' + waterArea.getInfo().toFixed(2) + ' km²' +
          ', built=' + builtArea.getInfo().toFixed(2) + ' km²');

      return {
        year: year,
        classifier: classifier,
        imagesUsed: result.imagesUsed,
        validKm2: validKm2,
        areas: areas,
        means: means,
        firstDate: result.firstDate,
        lastDate: result.lastDate
      };
    });

    results[districtKey + '_' + classifier] = yearlyResults;
  });
});

// =============================================================================
// HEADLINE CHANGES (2018 vs 2025)
// =============================================================================

print('\\n\\n========== HEADLINE CHANGES (2018 → 2025) ==========');

Object.keys(DISTRICTS).forEach(function(districtKey) {
  var district = DISTRICTS[districtKey];
  print('\\n--- ' + district.name + ' ---');

  ['spectral', 'dynamic_world'].forEach(function(classifier) {
    var key = districtKey + '_' + classifier;
    var y2018 = results[key].find(function(r) { return r.year === 2018; });
    var y2025 = results[key].find(function(r) { return r.year === 2025; });

    if (!y2018 || !y2025) {
      print('  ' + classifier + ': Missing data for 2018 or 2025');
      return;
    }

    print('  ' + classifier.toUpperCase() + ':');

    ['vegetation', 'water', 'built_bare'].forEach(function(cls) {
      var clsIdx = {vegetation: 2, water: 1, built_bare: 3}[cls];
      var area2018 = ee.Number(y2018.areas.classAreas.filter(ee.Filter.eq('class', clsIdx)).first().get('area'));
      var area2025 = ee.Number(y2025.areas.classAreas.filter(ee.Filter.eq('class', clsIdx)).first().get('area'));
      var valid2018 = y2018.validKm2;
      var valid2025 = y2025.validKm2;

      var pct2018 = area2018.divide(valid2018).multiply(100);
      var pct2025 = area2025.divide(valid2025).multiply(100);
      var changeKm2 = area2025.subtract(area2018);
      var changePct = changeKm2.divide(area2018).multiply(100);

      var label = {vegetation: 'Vegetation', water: 'Water', built_bare: 'Built-up/Bare'}[cls];
      print('    ' + label + ': ' +
          area2018.getInfo().toFixed(2) + ' → ' + area2025.getInfo().toFixed(2) + ' km² | ' +
          pct2018.getInfo().toFixed(1) + '% → ' + pct2025.getInfo().toFixed(1) + '% | ' +
          'change: ' + changeKm2.getInfo().toFixed(2) + ' km² (' + changePct.getInfo().toFixed(1) + '%)');
    });

    if (classifier === 'spectral') {
      var ndvi2018 = ee.Number(y2018.means.get('NDVI'));
      var ndvi2025 = ee.Number(y2025.means.get('NDVI'));
      print('    Mean NDVI: ' + ndvi2018.getInfo().toFixed(3) + ' → ' + ndvi2025.getInfo().toFixed(3) +
          ' | change: ' + ndvi2025.subtract(ndvi2018).getInfo().toFixed(3));
    }
  });
});

// =============================================================================
// EXPORT OPTIONS
// =============================================================================

// Uncomment to export results as CSV to Drive
/*
Export.table.toDrive({
  collection: ee.FeatureCollection(STUDY_YEARS.map(function(year) {
    return ee.Feature(null, {year: year, district: 'bengaluru_urban', classifier: 'spectral'});
  })),
  description: 'bengaluru_urban_spectral_stats',
  fileFormat: 'CSV'
});
*/

print('\\n\\nAnalysis complete! Check console for results.');
print('To export CSV, uncomment the Export.table.toDrive section at the bottom.');