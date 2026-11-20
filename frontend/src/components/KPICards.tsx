import React from 'react'
import { clsx } from 'clsx'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Info } from 'lucide-react'
import { Card } from './ui/Card'
import { YearlyStats, QualityFlags } from '../context/AppContext'

interface KPICardProps {
  label: string
  value: string
  change?: {
    absolute: number
    percent: number
  }
  unit: string
  color: 'green' | 'blue' | 'red' | 'gray'
  quality?: QualityFlags
  description?: string
}

function KPICard({ label, value, change, unit, color, quality, description }: KPICardProps) {
  const colorClasses = {
    green: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20',
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20',
    red: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20',
    gray: 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800',
  }

  const iconColorClasses = {
    green: 'text-green-500',
    blue: 'text-blue-500',
    red: 'text-red-500',
    gray: 'text-gray-500',
  }

  const getChangeColor = (val: number) => {
    if (val > 0) return 'text-green-600 dark:text-green-400'
    if (val < 0) return 'text-red-600 dark:text-red-400'
    return 'text-gray-500'
  }

  const getChangeIcon = (val: number) => {
    if (val > 0) return <TrendingUp className="w-4 h-4" aria-hidden="true" />
    if (val < 0) return <TrendingDown className="w-4 h-4" aria-hidden="true" />
    return <Minus className="w-4 h-4" aria-hidden="true" />
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{label}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{value} <span className="text-lg font-normal text-gray-500">{unit}</span></p>
          {description && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{description}</p>}
        </div>
        <div className={clsx('p-2 rounded-lg', colorClasses[color])}>
          <span className={iconColorClasses[color]}>●</span>
        </div>
      </div>

      {change !== undefined && (
        <div className="mt-3 flex items-center gap-2 text-sm">
          <span className={clsx('font-medium flex items-center gap-1', getChangeColor(change.percent))}>
            {getChangeIcon(change.percent)}
            {change.percent >= 0 ? '+' : ''}{change.percent.toFixed(1)}%
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            ({change.absolute >= 0 ? '+' : ''}{change.absolute.toFixed(2)} {unit})
          </span>
        </div>
      )}

      {quality && (quality.low_image_count || quality.low_coverage || quality.outlier_flag) && (
        <div className="mt-3 flex items-center gap-1.5 text-xs text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/30 rounded-lg p-2">
          <Info className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
          <span>
            {quality.low_image_count && `Low images (${quality.images_used}); `}
            {quality.low_coverage && `Low coverage (${quality.valid_coverage_pct.toFixed(1)}%); `}
            {quality.outlier_flag && `Outlier: ${quality.outlier_details}`}
          </span>
        </div>
      )}
    </Card>
  )
}

interface KPICardsProps {
  firstStats: YearlyStats | undefined
  lastStats: YearlyStats | undefined
  hasComparison: boolean
  firstYear: number
  lastYear: number
}

export function KPICards({ firstStats, lastStats, hasComparison, firstYear, lastYear }: KPICardsProps) {
  if (!firstStats || !lastStats || !hasComparison) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {['Vegetation', 'Water', 'Built-up/Bare', 'Mean NDVI'].map((label, i) => (
          <Card key={i} className="p-6 text-center text-gray-500">
            Select two different years to see change comparison
          </Card>
        ))}
      </div>
    )
  }

  const vegChange = {
    absolute: lastStats.vegetation_km2 - firstStats.vegetation_km2,
    percent: firstStats.vegetation_km2 > 0
      ? ((lastStats.vegetation_km2 - firstStats.vegetation_km2) / firstStats.vegetation_km2) * 100
      : 0,
  }

  const waterChange = {
    absolute: lastStats.water_km2 - firstStats.water_km2,
    percent: firstStats.water_km2 > 0
      ? ((lastStats.water_km2 - firstStats.water_km2) / firstStats.water_km2) * 100
      : 0,
  }

  const builtChange = {
    absolute: lastStats.built_bare_km2 - firstStats.built_bare_km2,
    percent: firstStats.built_bare_km2 > 0
      ? ((lastStats.built_bare_km2 - firstStats.built_bare_km2) / firstStats.built_bare_km2) * 100
      : 0,
  }

  const ndviChange = {
    absolute: lastStats.mean_ndvi - firstStats.mean_ndvi,
    percent: 0, // NDVI doesn't use percent change
  }

  // Generate plain-language descriptions
  const vegDesc = vegChange.absolute > 0
    ? `Vegetation increased by ${vegChange.absolute.toFixed(2)} km² (${vegChange.percent.toFixed(1)}%)`
    : `Vegetation decreased by ${Math.abs(vegChange.absolute).toFixed(2)} km² (${Math.abs(vegChange.percent).toFixed(1)}%)`

  const waterDesc = waterChange.absolute > 0
    ? `Water area increased by ${waterChange.absolute.toFixed(2)} km² (${waterChange.percent.toFixed(1)}%)`
    : `Water area decreased by ${Math.abs(waterChange.absolute).toFixed(2)} km² (${Math.abs(waterChange.percent).toFixed(1)}%)`

  const builtDesc = builtChange.absolute > 0
    ? `Built-up/bare increased by ${builtChange.absolute.toFixed(2)} km² (${builtChange.percent.toFixed(1)}%)`
    : `Built-up/bare decreased by ${Math.abs(builtChange.absolute).toFixed(2)} km² (${Math.abs(builtChange.percent).toFixed(1)}%)`

  const ndviDesc = ndviChange.absolute > 0
    ? `Mean NDVI increased by ${ndviChange.absolute.toFixed(3)}`
    : `Mean NDVI decreased by ${Math.abs(ndviChange.absolute).toFixed(3)}`

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <KPICard
        label={`Vegetation (${firstYear}→${lastYear})`}
        value={lastStats.vegetation_km2.toFixed(2)}
        change={vegChange}
        unit="km²"
        color="green"
        quality={lastStats.quality}
        description={vegDesc}
      />
      <KPICard
        label={`Water (${firstYear}→${lastYear})`}
        value={lastStats.water_km2.toFixed(2)}
        change={waterChange}
        unit="km²"
        color="blue"
        quality={lastStats.quality}
        description={waterDesc}
      />
      <KPICard
        label={`Built-up/Bare (${firstYear}→${lastYear})`}
        value={lastStats.built_bare_km2.toFixed(2)}
        change={builtChange}
        unit="km²"
        color="red"
        quality={lastStats.quality}
        description={builtDesc}
      />
      <KPICard
        label={`Mean NDVI (${firstYear}→${lastYear})`}
        value={lastStats.mean_ndvi.toFixed(3)}
        change={ndviChange}
        unit=""
        color="gray"
        quality={lastStats.quality}
        description={ndviDesc}
      />
    </div>
  )
}