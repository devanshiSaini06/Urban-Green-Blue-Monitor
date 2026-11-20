import React, { useEffect, useRef, useState, useMemo } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap, MapEvent } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useApp } from '../context/AppContext'
import { Card } from '../components/ui/Card'
import { YearSelector } from '../components/YearSelector'
import { SeasonSelector } from '../components/SeasonSelector'
import { ClassifierSelector } from '../components/ClassifierSelector'
import { ThresholdSliders } from '../components/ThresholdSliders'
import { Play, Pause, ChevronLeft, ChevronRight, Layers, Eye, EyeOff, Expand, Minimize2 } from 'lucide-react'
import { clsx } from 'clsx'

// Fix Leaflet default icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

interface MapLayerProps {
  tileUrl: string
  opacity: number
  attribution?: string
  zIndex?: number
}

function MapLayer({ tileUrl, opacity, attribution, zIndex = 200 }: MapLayerProps) {
  const map = useMap()

  useEffect(() => {
    if (!tileUrl) return

    const tileLayer = L.tileLayer(tileUrl, {
      opacity,
      attribution: attribution || '© Google Earth Engine',
      zIndex,
      maxZoom: 16,
      minZoom: 8,
    })

    tileLayer.addTo(map)

    return () => {
      map.removeLayer(tileLayer)
    }
  }, [tileUrl, opacity, attribution, zIndex, map])

  return null
}

function DistrictBoundary({ geojson, style, visible }: { geojson: any; style: any; visible: boolean }) {
  if (!visible || !geojson) return null

  return (
    <GeoJSON
      data={geojson}
      style={style}
      interactive={false}
    />
  )
}

// Layer control component
function LayerControls({
  layers,
  activeLayer,
  onLayerChange,
  opacity,
  onOpacityChange,
  showBoundary,
  onBoundaryToggle,
  year,
  onYearChange,
  minYear,
  maxYear,
  isPlaying,
  onPlayPause,
}: {
  layers: { id: string; name: string; icon: React.ReactNode }[]
  activeLayer: string
  onLayerChange: (layer: string) => void
  opacity: number
  onOpacityChange: (opacity: number) => void
  showBoundary: boolean
  onBoundaryToggle: () => void
  year: number
  onYearChange: (year: number) => void
  minYear: number
  maxYear: number
  isPlaying: boolean
  onPlayPause: () => void
}) {
  return (
    <div className="absolute top-4 right-4 z-20 flex flex-col gap-2">
      {/* Layer selector */}
      <Card className="p-2 map-layer-toggle">
        <div className="flex items-center gap-2 mb-2">
          <Layers className="w-4 h-4 text-gray-500" aria-hidden="true" />
          <span className="font-medium text-sm">Layers</span>
        </div>
        <div className="grid grid-cols-2 gap-1">
          {layers.map(layer => (
            <button
              key={layer.id}
              onClick={() => onLayerChange(layer.id)}
              className={clsx(
                'flex items-center gap-1.5 px-2 py-1.5 text-xs rounded transition-colors',
                activeLayer === layer.id
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                  : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
              )}
              aria-pressed={activeLayer === layer.id}
            >
              {layer.icon}
              {layer.name}
            </button>
          ))}
        </div>
      </Card>

      {/* Opacity & boundary */}
      <Card className="p-3 map-layer-toggle w-56">
        <div className="space-y-3">
          <div>
            <label className="label">Opacity</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={opacity}
              onChange={e => onOpacityChange(parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showBoundary}
              onChange={onBoundaryToggle}
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            Show boundary
          </label>
        </div>
      </Card>

      {/* Year slider */}
      <Card className="p-3 map-layer-toggle w-56">
        <div className="flex items-center justify-between mb-2">
          <span className="font-medium">Year: {year}</span>
          <button
            onClick={onPlayPause}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label={isPlaying ? 'Pause animation' : 'Play animation'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
        </div>
        <input
          type="range"
          min={minYear}
          max={maxYear}
          step={1}
          value={year}
          onChange={e => onYearChange(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <button
            onClick={() => onYearChange(Math.max(minYear, year - 1))}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            disabled={year <= minYear}
            aria-label="Previous year"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span>{minYear}</span>
          <span>{maxYear}</span>
          <button
            onClick={() => onYearChange(Math.min(maxYear, year + 1))}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            disabled={year >= maxYear}
            aria-label="Next year"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </Card>
    </div>
  )
}

const LAYER_CONFIG = [
  { id: 'true_color', name: 'True Color', icon: '🌍' },
  { id: 'ndvi', name: 'NDVI', icon: '🌿' },
  { id: 'mndwi', name: 'MNDWI', icon: '💧' },
  { id: 'ndbi', name: 'NDBI', icon: '🏗️' },
  { id: 'landcover', name: 'Land Cover', icon: '🗺️' },
  { id: 'change', name: 'Change', icon: '🔄' },
]

export function MapView() {
  const {
    analysisResult,
    selectedYears,
    mapLayer,
    setMapLayer,
    mapOpacity,
    setMapOpacity,
    showBoundary,
    setShowBoundary,
    compareYear,
    setCompareYear,
    baselineYear,
    season,
    classifier,
    thresholds,
    scale,
    runAnalysis,
    isLoading,
    districts,
    selectedDistrict,
  } = useApp()

  const [tileUrl, setTileUrl] = useState<string | null>(null)
  const [boundaryGeojson, setBoundaryGeojson] = useState<any>(null)
  const [mapYear, setMapYear] = useState(selectedYears[selectedYears.length - 1] || 2025)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const district = districts.find(d => d.id === selectedDistrict)
  const center = district?.center || [12.97, 77.59]
  const zoom = district?.zoom || 10

  // Fetch tile URL when parameters change
  useEffect(() => {
    if (!analysisResult || !selectedDistrict) return

    const fetchTile = async () => {
      try {
        const body = {
          layer: mapLayer,
          year: mapYear,
          district_id: selectedDistrict,
          classifier,
          season,
          thresholds,
        }
        if (baselineYear != null) body.baseline_year = baselineYear
        if (compareYear != null) body.compare_year = compareYear

        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/tiles`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (!response.ok) throw new Error('Failed to fetch tile URL')
        const data = await response.json()
        setTileUrl(data.tile_url)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load map layer')
        setTileUrl(null)
      }
    }

    fetchTile()
  }, [mapLayer, mapYear, selectedDistrict, classifier, season, thresholds, baselineYear, compareYear, analysisResult])

  // Fetch boundary GeoJSON
  useEffect(() => {
    if (!selectedDistrict) return

    const fetchBoundary = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/regions`)
        const data = await response.json()
        const district = data.find((d: any) => d.id === selectedDistrict)
        if (district) {
          // We'd need to fetch the actual GeoJSON from GEE
          // For now, create a simple bounding box polygon
          const bounds = district.bounds
          setBoundaryGeojson({
            type: 'Feature',
            geometry: {
              type: 'Polygon',
              coordinates: [[
                [bounds.west, bounds.south],
                [bounds.east, bounds.south],
                [bounds.east, bounds.north],
                [bounds.west, bounds.north],
                [bounds.west, bounds.south],
              ]],
            },
            properties: { name: district.display_name },
          })
        }
      } catch (err) {
        console.error('Failed to fetch boundary:', err)
      }
    }

    fetchBoundary()
  }, [selectedDistrict])

  // Animation loop
  useEffect(() => {
    if (!isPlaying) return

    const interval = setInterval(() => {
      setMapYear(prev => {
        const next = prev + 1
        return next > selectedYears[selectedYears.length - 1] ? selectedYears[0] : next
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [isPlaying, selectedYears])

  const handleYearChange = (year: number) => {
    setMapYear(year)
    setIsPlaying(false)
  }

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying)
  }

  const minYear = selectedYears[0] || 2018
  const maxYear = selectedYears[selectedYears.length - 1] || 2025

  if (!district) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 dark:text-gray-400">Please select a district first</p>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-200px)] min-h-[500px] relative">
      <MapContainer
        center={center as [number, number]}
        zoom={zoom}
        className="h-full w-full rounded-xl"
        scrollWheelZoom={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          zIndex={100}
        />

        {tileUrl && (
          <MapLayer
            tileUrl={tileUrl}
            opacity={mapOpacity}
            attribution="Google Earth Engine / Sentinel-2"
            zIndex={200}
          />
        )}

        <DistrictBoundary
          geojson={boundaryGeojson}
          style={{
            color: '#16a34a',
            weight: 2,
            fill: false,
            dashArray: '5, 5',
          }}
          visible={showBoundary}
        />

        <LayerControls
          layers={LAYER_CONFIG}
          activeLayer={mapLayer}
          onLayerChange={setMapLayer}
          opacity={mapOpacity}
          onOpacityChange={setMapOpacity}
          showBoundary={showBoundary}
          onBoundaryToggle={() => setShowBoundary(!showBoundary)}
          year={mapYear}
          onYearChange={handleYearChange}
          minYear={minYear}
          maxYear={maxYear}
          isPlaying={isPlaying}
          onPlayPause={handlePlayPause}
        />
      </MapContainer>

      {error && (
        <div className="absolute bottom-4 left-4 right-4 z-30">
          <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-3 text-red-700 dark:text-red-400 text-sm">
            {error}
          </div>
        </div>
      )}

      {!tileUrl && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 rounded-xl z-10">
          <div className="text-center p-6">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Loading map layer…</p>
          </div>
        </div>
      )}

      {/* Controls panel */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
        <YearSelector />
        <SeasonSelector />
        <ClassifierSelector />
        <ThresholdSliders />
      </div>
    </div>
  )
}