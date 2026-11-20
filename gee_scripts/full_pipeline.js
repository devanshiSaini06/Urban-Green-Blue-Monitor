/**
 * Urban Green and Blue Change Monitor - Full Processing Pipeline
 * GEE Code Editor Script
 *
 * This script runs the complete analysis pipeline for both districts
 * and exports results as CSV to Google Drive.
 *
 * Run in Google Earth Engine Code Editor: https://code.earthengine.google.com/
 *
 * Requirements:
 * - GEE project: graphic-tide-513321-m3
 * - Assets: projects/graphic-tide-513321-m3/assets/Bengaluru (feature 1)
 *           projects/graphic-tide-513321-m3/assets/GautamBuddhaNagar (feature 0)
 */

// =============================================================================
// USER CONFIGURATION
// =============================================================================
var CONFIG = {
  projectId: 'graphic-tide-513321-m3',
  studyYears: [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  season: 'oct-dec',  // 'oct-dec', 'jan-mar', 'mar-may', 'jun-sep'
  scale: 20,
  cloudThreshold: 80,
  exportCrs: 'EPSG:32643',
  driveFolder: 'UGBM_Results',  // Google Drive folder for exports
  classifiers: ['spectral', 'dynamic_world'],
  thresholds: {
    mndwi_water: 0.10,
    ndvi_water_max: 0.15,
    ndvi_veg_min: 0.35,
    ndbi_built_min: 0.0,
    ndvi_built_max: 0.20
  }
};

// District configuration
var DISTRICTS = {
  bengaluru_urban: {
    assetId: 'projects/graphic-tide-513321-m3/assets/Bengaluru',
    featureIndex: 1,
    name: 'Bengaluru_Urban'
  },
  gautam_buddha_nagar: {
    assetId: 'projects/graphic-tide-513321-m3/assets/GautamBuddhaNagar',
    featureIndex: 0,
    name: 'Gautam_Buddha_Nagar'
  }
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/** Get district geometry */
function getDistrictGeometry(districtKey) {
  var district = DISTRICTS[districtKey];
  var fc = ee.FeatureCollection(district.assetId);
  var feature = fc.toList(fc.size()).get(district.featureIndex);
  return ee.Feature(feature).geometry();
}

/** Get season date range */
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

/** Cloud mask using SCL */
function maskSentinel2Clouds(image) {
  var scl = image.select('SCL');
  var mask = scl.neq(0).and(scl.neq(1)).and(scl.neq(3))
      .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return image.updateMask(mask)
      .select(['B2','B3','B4','B8','B11','B12'])
      .multiply(0.0001)
      .copyProperties(image, ['system:time_start', 'system:index_id', 'CLOUDY_PIXEL_PERCENTAGE']);
}

/** Compute indices */
function computeIndices(image) {
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');
  var mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  var ndbi = image.normalizedDifference(['B11', 'B8']).rename('NDBI');
  return image.addBands([ndvi, ndwi, mndwi, ndbi]);
}

/** Spectral classification */
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

  var remap = ee.Image.constant([
    [0, 1], [1, 2], [2, 2], [3, 1], [4, 2], [5, 2], [6, 3], [7, 3], [8, 4]
  ]);
  return dw.remap(remap.slice(1, 0), remap.slice(1, 1), 4, 'landcover').byte();
}

/** Compute area statistics */
function computeAreas(classification, geometry, scale) {
  var pixelArea = ee.Image.pixelArea().divide(1e6);
  var classWithArea = classification.addBands(pixelArea.rename('area_km2'));

  var stats = classWithArea.reduceRegion({
    reducer: ee.Reducer.sum().group({groupField: 0, groupName: 'class'}),
    geometry: geometry,
    scale: scale,
    maxPixels: 1e13,
    bestEffort: true,
    crs: CONFIG.exportCrs
  });

  var validArea = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: geometry,
    scale: scale,
    maxPixels: 1e13,
    bestEffort: true,
    crs: CONFIG.exportCrs
  }).get('area_km2');

  var groups = ee.List(stats.get('groups'));
  var validKm2 = ee.Number(validArea);

  // Convert groups to feature collection for export
  var features = groups.map(function(group) {
    group = ee.Dictionary(group);
    var classId = ee.Number(group.get('class')).int();
    var area = ee.Number(group.get('sum'));
    var classNames = {1: 'water', 2: 'vegetation', 3: 'built_bare', 4: 'other'};
    return ee.Feature(null, {
      class: classId,
      class_name: classNames[classId],
      area_km2: area
    });
  });

  return {
    features: ee.FeatureCollection(features),
    validKm2: validKm2
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
    crs: CONFIG.exportCrs
  });
}

/** Run analysis for one year */
function analyzeYear(districtKey, year, classifier) {
  var district = DISTRICTS[districtKey];
  var geometry = getDistrictGeometry(districtKey);
  var dates = getSeasonDates(year, CONFIG.season);
  var startDate = dates[0];
  var endDate = dates[1];

  var rawAreaKm2 = geometry.area(1).divide(1e6);

  if (classifier === 'spectral') {
    var collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(geometry)
        .filterDate(startDate, endDate)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CONFIG.cloudThreshold))
        .map(maskSentinel2Clouds);

    var imagesUsed = collection.size();
    var composite = collection.median().clip(geometry);
    composite = computeIndices(composite);
    composite = classifySpectral(composite, CONFIG.thresholds);

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

/** Process all years for a district/classifier combination */
function processDistrictClassifier(districtKey, classifier) {
  var district = DISTRICTS[districtKey];
  print('\\nProcessing ' + district.name + ' - ' + classifier);

  var yearlyResults = CONFIG.studyYears.map(function(year) {
    var result = analyzeYear(districtKey, year, classifier);

    var areas = computeAreas(
        result.composite.select('landcover'),
        result.geometry,
        CONFIG.scale
    );

    var means = classifier === 'spectral'
        ? computeMeanIndices(result.composite, result.geometry, CONFIG.scale)
        : {NDVI: 0, MNDWI: 0, NDBI: 0};

    // Create feature for each class area
    var classFeatures = areas.features.map(function(f) {
      f = ee.Feature(f);
      return f.set({
        year: year,
        district: district.name,
        classifier: classifier,
        images_used: result.imagesUsed,
        valid_km2: areas.validKm2,
        raw_district_km2: result.rawAreaKm2,
        mean_ndvi: means.NDVI,
        mean_mndwi: means.MNDWI,
        mean_ndbi: means.NDBI,
        composite_first_date: result.firstDate,
        composite_last_date: result.lastDate
      });
    });

    // Also create summary feature
    var summary = ee.Feature(null, {
      year: year,
      district: district.name,
      classifier: classifier,
      type: 'summary',
      images_used: result.imagesUsed,
      valid_km2: areas.validKm2,
      raw_district_km2: result.rawAreaKm2,
      mean_ndvi: means.NDVI,
      mean_mndwi: means.MNDWI,
      mean_ndbi: means.NDBI,
      composite_first_date: result.firstDate,
      composite_last_date: result.lastDate
    });

    // Add class areas to summary
    var classAreas = areas.features.map(function(f) {
      return ee.Dictionary({class: f.get('class_name'), area: f.get('area_km2')});
    });
    summary = summary.set('class_areas', classAreas);

    return ee.FeatureCollection(classFeatures.merge(ee.FeatureCollection([summary])));
  });

  return ee.FeatureCollection(yearlyResults).flatten();
}

/** Compute trend statistics (server-side approximation) */
function computeTrends(fc, variable) {
  // This is a simplified version - full trends computed in Python
  // Here we just add the raw values for export
  return fc;
}

// =============================================================================
// MAIN EXECUTION
// =============================================================================

print('Starting Urban Green and Blue Change Monitor Pipeline');
print('Study years: ' + CONFIG.studyYears.join(', '));
print('Season: ' + CONFIG.season);
print('Scale: ' + CONFIG.scale + 'm');
print('Classifiers: ' + CONFIG.classifiers.join(', '));

var allResults = [];

CONFIG.classifiers.forEach(function(classifier) {
  Object.keys(DISTRICTS).forEach(function(districtKey) {
    var result = processDistrictClassifier(districtKey, classifier);
    allResults.push(result);
  });
});

// Merge all results
var mergedResults = ee.FeatureCollection(allResults).flatten();

// Export to Google Drive as CSV
Export.table.toDrive({
  collection: mergedResults,
  description: 'UGBM_LandCover_Statistics_' + CONFIG.season,
  folder: CONFIG.driveFolder,
  fileNamePrefix: 'landcover_stats_' + CONFIG.season + '_' + Date.now(),
  fileFormat: 'CSV',
  selectors: [
    'year', 'district', 'classifier', 'type', 'class', 'class_name',
    'images_used', 'valid_km2', 'raw_district_km2',
    'area_km2', 'mean_ndvi', 'mean_mndwi', 'mean_ndbi',
    'composite_first_date', 'composite_last_date'
  ]
});

print('\\nExport task submitted to Google Drive.');
print('Check Tasks tab to monitor progress.');
print('Results will be saved to Drive folder: ' + CONFIG.driveFolder);

// =============================================================================
// ADDITIONAL EXPORTS
// =============================================================================

// Export just summary statistics (one row per year/district/classifier)
var summaries = mergedResults.filter(ee.Filter.eq('type', 'summary'));
Export.table.toDrive({
  collection: summaries,
  description: 'UGBM_Summary_Statistics_' + CONFIG.season,
  folder: CONFIG.driveFolder,
  fileNamePrefix: 'summary_stats_' + CONFIG.season + '_' + Date.now(),
  fileFormat: 'CSV',
  selectors: [
    'year', 'district', 'classifier',
    'images_used', 'valid_km2', 'raw_district_km2',
    'mean_ndvi', 'mean_mndwi', 'mean_ndbi',
    'composite_first_date', 'composite_last_date',
    'class_areas'
  ]
});

// Export land cover maps for visualization
Object.keys(DISTRICTS).forEach(function(districtKey) {
  var district = DISTRICTS[districtKey];
  var geometry = getDistrictGeometry(districtKey);

  CONFIG.studyYears.forEach(function(year) {
    var dates = getSeasonDates(year, CONFIG.season);
    var composite = null;

    // Spectral
    var collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(geometry)
        .filterDate(dates[0], dates[1])
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CONFIG.cloudThreshold))
        .map(maskSentinel2Clouds);

    composite = collection.median().clip(geometry);
    composite = computeIndices(composite);
    composite = classifySpectral(composite, CONFIG.thresholds);

    // Export landcover map
    Export.image.toDrive({
      image: composite.select('landcover').byte(),
      description: district.name + '_' + year + '_landcover_spectral',
      folder: CONFIG.driveFolder + '/maps',
      scale: CONFIG.scale,
      crs: CONFIG.exportCrs,
      region: geometry,
      maxPixels: 1e13,
      fileFormat: 'GeoTIFF'
    });

    // Dynamic World
    var dwComposite = classifyDynamicWorld(geometry, dates[0], dates[1]);
    Export.image.toDrive({
      image: dwComposite.byte(),
      description: district.name + '_' + year + '_landcover_dw',
      folder: CONFIG.driveFolder + '/maps',
      scale: CONFIG.scale,
      crs: CONFIG.exportCrs,
      region: geometry,
      maxPixels: 1e13,
      fileFormat: 'GeoTIFF'
    });
  });
});

print('\\nAll export tasks submitted!');
print('Check the Tasks tab in the Code Editor to monitor progress.');
print('Maps will be in Drive folder: ' + CONFIG.driveFolder + '/maps');
print('Statistics will be in Drive folder: ' + CONFIG.driveFolder);