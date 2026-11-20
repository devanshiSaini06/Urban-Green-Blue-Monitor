import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

// Types matching backend schemas
export interface District {
  id: string
  name: string
  display_name: string
  bounds: { west: number; south: number; east: number; north: number }
  center: [number, number]
  zoom: number
}

export interface YearlyStats {
  year: number
  images_used: number
  valid_km2: number
  vegetation_km2: number
  water_km2: number
  built_bare_km2: number
  other_km2: number
  vegetation_pct: number
  water_pct: number
  built_bare_pct: number
  other_pct: number
  mean_ndvi: number
  mean_mndwi: number
  mean_ndbi: number
  composite_first_date: string | null
  composite_last_date: string | null
  quality: QualityFlags
  raw_district_km2: number
}

export interface QualityFlags {
  low_image_count: boolean
  low_coverage: boolean
  outlier_flag: boolean
  outlier_details: string | null
  images_used: number
  valid_coverage_pct: number
}

export interface AnalysisResult {
  district_id: string | null
  years: number[]
  season: SeasonWindow
  classifier: string
  thresholds: Thresholds
  scale: number
  baseline_year: number | null
  stats: YearlyStats[]
  recommended_baseline_year: number
  quality_summary: QualitySummary
  run_metadata: RunMetadata
}

export interface SeasonWindow {
  name: string
  start_month: number | null
  end_month: number | null
  custom_start: string | null
  custom_end: string | null
}

export interface Thresholds {
  mndwi_water: number
  ndvi_water_max: number
  ndvi_veg_min: number
  ndbi_built_min: number
  ndvi_built_max: number
}

export interface QualitySummary {
  years_with_warnings: number
  outlier_years: number[]
  best_quality_year: number
}

export interface RunMetadata {
  run_date: string
  gee_project: string
  sentinel_collection: string
  dynamic_world_collection: string
  scale_m: number
  crs: string
  cloud_threshold: number
  classifier: string
  thresholds: Thresholds
  season: SeasonWindow
  district: string
}

interface AppState {
  // UI State
  selectedDistrict: string | null
  selectedYears: number[]
  compareYear: number | null
  baselineYear: number | null
  season: SeasonWindow
  classifier: 'spectral' | 'dynamic_world'
  thresholds: Thresholds
  cloudThreshold: number
  scale: number
  mapLayer: MapLayer
  mapOpacity: number
  showBoundary: boolean

  // Data
  districts: District[]
  analysisResult: AnalysisResult | null
  isLoading: boolean
  error: string | null

  // Actions
  setDistrict: (id: string) => void
  setYears: (years: number[]) => void
  setCompareYear: (year: number | null) => void
  setBaselineYear: (year: number | null) => void
  setSeason: (season: SeasonWindow) => void
  setClassifier: (classifier: 'spectral' | 'dynamic_world') => void
  setThresholds: (thresholds: Partial<Thresholds>) => void
  setCloudThreshold: (value: number) => void
  setScale: (value: number) => void
  setMapLayer: (layer: MapLayer) => void
  setMapOpacity: (opacity: number) => void
  setShowBoundary: (show: boolean) => void
  fetchDistricts: () => Promise<void>
  runAnalysis: () => Promise<void>
  clearError: () => void
  resetToDefaults: () => void
  syncFromUrl: () => void
  syncToUrl: () => void
}

export type MapLayer =
  | 'true_color'
  | 'ndvi'
  | 'mndwi'
  | 'ndbi'
  | 'landcover'
  | 'change_since_baseline'
  | 'year_to_year'

const DEFAULT_THRESHOLDS: Thresholds = {
  mndwi_water: 0.10,
  ndvi_water_max: 0.15,
  ndvi_veg_min: 0.35,
  ndbi_built_min: 0.0,
  ndvi_built_max: 0.20,
}

const DEFAULT_SEASON: SeasonWindow = {
  name: 'oct-dec',
  start_month: 10,
  end_month: 1,
  custom_start: null,
  custom_end: null,
}

const STUDY_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

const AppContext = createContext<AppState | undefined>(undefined)

export function AppProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams()

  // State
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(() => {
    return searchParams.get('district') || 'bengaluru_urban'
  })
  const [selectedYears, setSelectedYears] = useState<number[]>(() => {
    const years = searchParams.get('years')?.split(',').map(Number) || [2018, 2025]
    return years.filter(y => STUDY_YEARS.includes(y))
  })
  const [compareYear, _setCompareYear] = useState<number | null>(() => {
    const yr = searchParams.get('compare')
    return yr ? Number(yr) : null
  })
  const [baselineYear, _setBaselineYear] = useState<number | null>(() => {
    const yr = searchParams.get('baseline')
    return yr ? Number(yr) : null
  })
  const [season, setSeasonState] = useState<SeasonWindow>(() => {
    const s = searchParams.get('season')
    if (s) return JSON.parse(s)
    return DEFAULT_SEASON
  })
  const [classifier, setClassifierState] = useState<'spectral' | 'dynamic_world'>(() => {
    return (searchParams.get('classifier') as 'spectral' | 'dynamic_world') || 'spectral'
  })
  const [thresholds, setThresholdsState] = useState<Thresholds>(() => {
    const t = searchParams.get('thresholds')
    if (t) return JSON.parse(t)
    return DEFAULT_THRESHOLDS
  })
  const [cloudThreshold, setCloudThresholdState] = useState<number>(() => {
    const c = searchParams.get('cloud')
    return c ? Number(c) : 80
  })
  const [scale, setScaleState] = useState<number>(() => {
    const s = searchParams.get('scale')
    return s ? Number(s) : 20
  })
  const [mapLayer, setMapLayerState] = useState<MapLayer>(() => {
    return (searchParams.get('layer') as MapLayer) || 'landcover'
  })
  const [mapOpacity, setMapOpacityState] = useState<number>(() => {
    const o = searchParams.get('opacity')
    return o ? Number(o) : 1
  })
  const [showBoundary, setShowBoundaryState] = useState<boolean>(() => {
    return searchParams.get('boundary') === 'true'
  })

  const [districts, setDistricts] = useState<District[]>([])
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // API base URL
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // Sync from URL on mount
  useEffect(() => {
    syncFromUrl()
    fetchDistricts()
  }, [])

  // Sync to URL when state changes
  const syncToUrl = useCallback(() => {
    const params = new URLSearchParams()
    if (selectedDistrict) params.set('district', selectedDistrict)
    if (selectedYears.length > 0) params.set('years', selectedYears.join(','))
    if (compareYear) params.set('compare', String(compareYear))
    if (baselineYear) params.set('baseline', String(baselineYear))
    params.set('season', JSON.stringify(season))
    params.set('classifier', classifier)
    params.set('thresholds', JSON.stringify(thresholds))
    params.set('cloud', String(cloudThreshold))
    params.set('scale', String(scale))
    params.set('layer', mapLayer)
    params.set('opacity', String(mapOpacity))
    params.set('boundary', String(showBoundary))
    setSearchParams(params, { replace: true })
  }, [
    selectedDistrict, selectedYears, compareYear, baselineYear,
    season, classifier, thresholds, cloudThreshold, scale,
    mapLayer, mapOpacity, showBoundary, setSearchParams
  ])

  const syncFromUrl = useCallback(() => {
    const district = searchParams.get('district')
    if (district) setSelectedDistrict(district)

    const years = searchParams.get('years')?.split(',').map(Number)
    if (years) setSelectedYears(years.filter(y => STUDY_YEARS.includes(y)))

    const compare = searchParams.get('compare')
    if (compare) setCompareYear(Number(compare))

    const baseline = searchParams.get('baseline')
    if (baseline) setBaselineYear(Number(baseline))

    const s = searchParams.get('season')
    if (s) setSeasonState(JSON.parse(s))

    const c = searchParams.get('classifier')
    if (c) setClassifierState(c as 'spectral' | 'dynamic_world')

    const t = searchParams.get('thresholds')
    if (t) setThresholdsState(JSON.parse(t))

    const cl = searchParams.get('cloud')
    if (cl) setCloudThresholdState(Number(cl))

    const sc = searchParams.get('scale')
    if (sc) setScaleState(Number(sc))

    const l = searchParams.get('layer')
    if (l) setMapLayerState(l as MapLayer)

    const o = searchParams.get('opacity')
    if (o) setMapOpacityState(Number(o))

    const b = searchParams.get('boundary')
    if (b) setShowBoundaryState(b === 'true')
  }, [searchParams])

  // Actions
  const setDistrict = useCallback((id: string) => {
    setSelectedDistrict(id)
    syncToUrl()
  }, [syncToUrl])

  const setYears = useCallback((years: number[]) => {
    setSelectedYears(years)
    syncToUrl()
  }, [syncToUrl])

  const setCompareYear = useCallback((year: number | null) => {
    _setCompareYear(year)
    syncToUrl()
  }, [syncToUrl])

  const setBaselineYear = useCallback((year: number | null) => {
    _setBaselineYear(year)
    syncToUrl()
  }, [syncToUrl])

  const setSeason = useCallback((s: SeasonWindow) => {
    setSeasonState(s)
    syncToUrl()
  }, [syncToUrl])

  const setClassifier = useCallback((c: 'spectral' | 'dynamic_world') => {
    setClassifierState(c)
    syncToUrl()
  }, [syncToUrl])

  const setThresholds = useCallback((t: Partial<Thresholds>) => {
    setThresholdsState(prev => ({ ...prev, ...t }))
    syncToUrl()
  }, [syncToUrl])

  const setCloudThreshold = useCallback((value: number) => {
    setCloudThresholdState(value)
    syncToUrl()
  }, [syncToUrl])

  const setScale = useCallback((value: number) => {
    setScaleState(value)
    syncToUrl()
  }, [syncToUrl])

  const setMapLayer = useCallback((layer: MapLayer) => {
    setMapLayerState(layer)
    syncToUrl()
  }, [syncToUrl])

  const setMapOpacity = useCallback((opacity: number) => {
    setMapOpacityState(opacity)
    syncToUrl()
  }, [syncToUrl])

  const setShowBoundary = useCallback((show: boolean) => {
    setShowBoundaryState(show)
    syncToUrl()
  }, [syncToUrl])

  const clearError = useCallback(() => setError(null), [])

  const resetToDefaults = useCallback(() => {
    setSelectedDistrict('bengaluru_urban')
    setSelectedYears([2018, 2025])
    setCompareYear(null)
    setBaselineYear(null)
    setSeasonState(DEFAULT_SEASON)
    setClassifierState('spectral')
    setThresholdsState(DEFAULT_THRESHOLDS)
    setCloudThresholdState(80)
    setScaleState(20)
    setMapLayerState('landcover')
    setMapOpacityState(1)
    setShowBoundaryState(true)
    setAnalysisResult(null)
    setError(null)
    syncToUrl()
  }, [syncToUrl])

  const fetchDistricts = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/regions`)
      if (!response.ok) throw new Error('Failed to fetch districts')
      const data = await response.json()
      setDistricts(data)
    } catch (err) {
      console.error('Failed to fetch districts:', err)
    }
  }, [apiUrl])

  const runAnalysis = useCallback(async () => {
    if (!selectedDistrict) {
      setError('Please select a district')
      return
    }
    if (selectedYears.length === 0) {
      setError('Please select at least one year')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const requestBody = {
        district_id: selectedDistrict,
        years: selectedYears,
        season,
        classifier,
        thresholds,
        cloud_threshold: cloudThreshold,
        scale,
        baseline_year: baselineYear,
      }

      const response = await fetch(`${apiUrl}/api/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Analysis failed')
      }

      const data = await response.json()
      setAnalysisResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setIsLoading(false)
    }
  }, [
    selectedDistrict, selectedYears, season, classifier, thresholds,
    cloudThreshold, scale, baselineYear, apiUrl
  ])

  const value: AppState = {
    selectedDistrict,
    selectedYears,
    compareYear,
    baselineYear,
    season,
    classifier,
    thresholds,
    cloudThreshold,
    scale,
    mapLayer,
    mapOpacity,
    showBoundary,
    districts,
    analysisResult,
    isLoading,
    error,
    setDistrict,
    setYears,
    setCompareYear,
    setBaselineYear,
    setSeason,
    setClassifier,
    setThresholds,
    setCloudThreshold,
    setScale,
    setMapLayer,
    setMapOpacity,
    setShowBoundary,
    fetchDistricts,
    runAnalysis,
    clearError,
    resetToDefaults,
    syncFromUrl,
    syncToUrl,
  }

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}