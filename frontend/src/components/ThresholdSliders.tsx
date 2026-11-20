import React, { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Card } from './ui/Card'
import { ChevronDown, ChevronUp, SlidersHorizontal } from 'lucide-react'
import { clsx } from 'clsx'

const THRESHOLDS = [
  { key: 'mndwi_water', label: 'MNDWI > Water', min: -0.5, max: 0.5, step: 0.01, default: 0.10 },
  { key: 'ndvi_water_max', label: 'NDVI < Water (max)', min: 0, max: 1, step: 0.01, default: 0.15 },
  { key: 'ndvi_veg_min', label: 'NDVI ≥ Vegetation', min: 0, max: 1, step: 0.01, default: 0.35 },
  { key: 'ndbi_built_min', label: 'NDBI > Built-up', min: -0.5, max: 0.5, step: 0.01, default: 0.0 },
  { key: 'ndvi_built_max', label: 'NDVI < Built-up (max)', min: 0, max: 1, step: 0.01, default: 0.20 },
] as const

export function ThresholdSliders() {
  const { thresholds, setThresholds, classifier } = useApp()
  const [isOpen, setIsOpen] = useState(false)

  if (classifier !== 'spectral') {
    return null
  }

  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-5 h-5 text-gray-500" aria-hidden="true" />
          <span className="font-medium text-gray-900 dark:text-gray-100">Classification Thresholds</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">(Spectral classifier only)</span>
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-gray-500" /> : <ChevronDown className="w-5 h-5 text-gray-500" />}
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-200 dark:border-gray-700">
          {THRESHOLDS.map(({ key, label, min, max, step, default: defaultValue }) => (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-sm text-gray-700 dark:text-gray-300">{label}</label>
                <span className="text-sm font-mono text-primary-600 dark:text-primary-400">
                  {thresholds[key as keyof typeof thresholds].toFixed(step < 0.1 ? 2 : 1)}
                </span>
              </div>
              <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={thresholds[key as keyof typeof thresholds]}
                onChange={e => setThresholds({ [key]: parseFloat(e.target.value) })}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                aria-label={label}
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Min: {min}</span>
                <span>Default: {defaultValue}</span>
                <span>Max: {max}</span>
              </div>
            </div>
          ))}

          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setThresholds({
                mndwi_water: 0.10,
                ndvi_water_max: 0.15,
                ndvi_veg_min: 0.35,
                ndbi_built_min: 0.0,
                ndvi_built_max: 0.20,
              })}
              className="btn-ghost btn-sm"
            >
              Reset to defaults
            </button>
          </div>
        </div>
      )}
    </Card>
  )
}