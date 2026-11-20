import React from 'react'
import { useApp } from '../context/AppContext'
import { Card } from '../components/ui/Card'
import { Skeleton } from '../components/ui/Skeleton'
import { BarChart2, TrendingUp, AlertTriangle, Table, GitBranch, LayoutGrid, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { clsx } from 'clsx'

const ANALYSIS_TABS = [
  { id: 'trends', label: 'Trends', icon: TrendingUp },
  { id: 'transitions', label: 'Transitions', icon: GitBranch },
  { id: 'landscape', label: 'Landscape Metrics', icon: LayoutGrid },
  { id: 'urban', label: 'Urban Growth', icon: BarChart2 },
  { id: 'environmental', label: 'Environmental', icon: AlertTriangle },
  { id: 'lakes', label: 'Lakes', icon: GitBranch },
  { id: 'hotspots', label: 'Hotspots', icon: LayoutGrid },
] as const

// Helper to format numbers
function formatNumber(num: number | undefined, decimals = 2): string {
  if (num === undefined || num === null) return '—'
  if (num >= 1000) return (num / 1000).toFixed(decimals) + 'k'
  return num.toFixed(decimals)
}

function formatPct(num: number | undefined): string {
  if (num === undefined || num === null) return '—'
  return num.toFixed(1) + '%'
}

function getTrendIcon(current: number, previous: number) {
  if (current > previous) return <ArrowUpRight className="w-4 h-4 text-green-600" />
  if (current < previous) return <ArrowDownRight className="w-4 h-4 text-red-600" />
  return <Minus className="w-4 h-4 text-gray-400" />
}

export function AnalysisPage() {
  const { analysisResult, isLoading, runAnalysis, selectedYears } = useApp()
  const [activeTab, setActiveTab] = React.useState<'trends' | 'transitions' | 'landscape' | 'urban' | 'environmental' | 'lakes' | 'hotspots'>('trends')

  if (isLoading) {
    return (
      <div className="space-y-6">
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="p-6"><Skeleton className="h-64 w-full" /></Card>
        ))}
      </div>
    )
  }

  if (!analysisResult) {
    return (
      <div className="text-center py-12">
        <BarChart2 className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Run an analysis first
        </h2>
        <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto mb-6">
          Go to the Dashboard, select your parameters, and run an analysis to see detailed
          trend statistics, transition matrices, and other advanced analytics.
        </p>
        <button onClick={runAnalysis} className="btn-primary" disabled={isLoading}>
          Run Analysis
        </button>
      </div>
    )
  }

  const hasTrendData = selectedYears.length >= 3
  const stats = analysisResult.stats || []

  return (
    <div className="space-y-6">
      {/* Tab navigation */}
      <div className="flex flex-wrap gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1" role="tablist">
        {ANALYSIS_TABS.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-colors',
              activeTab === tab.id
                ? 'bg-white text-primary-700 shadow-sm dark:bg-gray-700 dark:text-primary-300'
                : 'text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100'
            )}
            disabled={tab.id === 'trends' && !hasTrendData}
          >
            <tab.icon className="w-4 h-4" aria-hidden="true" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="space-y-6">
        {activeTab === 'trends' && <TrendsTab stats={stats} hasData={hasTrendData} />}
        {activeTab === 'transitions' && <TransitionsTab stats={stats} />}
        {activeTab === 'landscape' && <LandscapeTab stats={stats} />}
        {activeTab === 'urban' && <UrbanGrowthTab stats={stats} />}
        {activeTab === 'environmental' && <EnvironmentalTab stats={stats} />}
        {activeTab === 'lakes' && <LakesTab stats={stats} />}
        {activeTab === 'hotspots' && <HotspotsTab stats={stats} />}
      </div>
    </div>
  )
}

function TrendsTab({ stats, hasData }: { stats: any[]; hasData: boolean }) {
  if (!hasData) {
    return (
      <Card className="p-8 text-center">
        <TrendingUp className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          Insufficient data for trend analysis
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Select at least 3 years to compute Mann-Kendall trend test, Sen's slope,
          and linear regression with confidence intervals.
        </p>
      </Card>
    )
  }

  if (stats.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-gray-600 dark:text-gray-400">No statistics available</p>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card>
        <h3 className="font-semibold mb-4">Land Cover Trends Over Time</h3>
        <div className="space-y-4">
          {['Vegetation', 'Water', 'Built-up/Bare', 'Other'].map((label, idx) => {
            const key = label.toLowerCase().replace('/', '_').replace('-', '_') + '_pct'
            return (
              <div key={label} className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{label}</span>
                  <span className="text-sm text-gray-500">
                    {stats.map(s => s[key]).filter(v => v !== undefined).length} years of data
                  </span>
                </div>
                <div className="flex items-center gap-2 overflow-x-auto pb-2">
                  {stats.map((s, i) => {
                    const val = s[key]
                    const prevVal = i > 0 ? stats[i - 1][key] : undefined
                    return (
                      <div key={s.year} className="flex flex-col items-center min-w-[60px]">
                        <span className="text-xs text-gray-500">{s.year}</span>
                        <div className="flex items-center gap-1">
                          <span className="font-mono text-lg font-semibold">{formatPct(val)}</span>
                          {prevVal !== undefined && getTrendIcon(val, prevVal)}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Key Metrics Summary</h3>
        <div className="space-y-4">
          {['Vegetation', 'Water', 'Built-up/Bare', 'Mean NDVI'].map((metric, i) => {
            const keyMap: Record<string, string> = {
              'Vegetation': 'vegetation_pct',
              'Water': 'water_pct',
              'Built-up/Bare': 'built_bare_pct',
              'Mean NDVI': 'mean_ndvi',
            }
            const key = keyMap[metric]
            const values = stats.map(s => s[key]).filter(v => v !== undefined)
            const latest = values[values.length - 1]
            const first = values[0]
            const change = (first !== undefined && latest !== undefined) ? latest - first : undefined
            return (
              <div key={metric} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div>
                  <span className="font-medium">{metric}</span>
                  <div className="text-sm text-gray-500">
                    Range: {values.length > 0 ? Math.min(...values).toFixed(1) : '—'} – {values.length > 0 ? Math.max(...values).toFixed(1) : '—'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-1 justify-end">
                    <span className="font-mono font-semibold">{key === 'mean_ndvi' ? (latest !== undefined ? latest.toFixed(3) : '—') : formatPct(latest)}</span>
                    {change !== undefined && getTrendIcon(change, 0)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {change !== undefined ? (change > 0 ? `+${change.toFixed(1)}%` : change.toFixed(1) + '%') : '—'} total change
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}

function TransitionsTab({ stats }: { stats: any[] }) {
  if (stats.length < 2) {
    return (
      <Card className="p-8 text-center">
        <GitBranch className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          Need at least 2 years for transitions
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Select multiple years to see land cover transition matrices.
        </p>
      </Card>
    )
  }

  // Compute approximate transitions from year-over-year changes
  const classes = [
    { key: 'water_km2', label: 'Water', color: 'blue-500' },
    { key: 'vegetation_km2', label: 'Vegetation', color: 'green-500' },
    { key: 'built_bare_km2', label: 'Built-up/Bare', color: 'amber-500' },
    { key: 'other_km2', label: 'Other', color: 'gray-500' },
  ]

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-semibold mb-4">Year-over-Year Area Changes (km²)</h3>
        <div className="table-container overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left p-3 font-medium">Transition</th>
                {classes.map(c => (
                  <th key={c.label} className="text-right p-3 font-medium">{c.label}</th>
                ))}
                <th className="text-right p-3 font-medium">Net Change</th>
              </tr>
            </thead>
            <tbody>
              {stats.slice(1).map((curr, i) => {
                const prev = stats[i]
                return (
                  <tr key={curr.year} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="p-3 font-medium">{prev.year} → {curr.year}</td>
                    {classes.map(c => {
                      const change = curr[c.key] - prev[c.key]
                      return (
                        <td key={c.label} className="p-3 text-right font-mono">
                          <span className={clsx(
                            'font-semibold',
                            change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-500'
                          )}>
                            {change >= 0 ? '+' : ''}{formatNumber(change, 3)}
                          </span>
                        </td>
                      )
                    })}
                    <td className="p-3 text-right font-mono font-semibold">
                      {classes.reduce((sum, c) => sum + (curr[c.key] - prev[c.key]), 0).toFixed(3)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Current Year Composition (Latest Year)</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {classes.map(c => {
            const latest = stats[stats.length - 1]
            const pct = latest[`${c.key.replace('_km2', '_pct')}`]
            return (
              <div key={c.label} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                <div className="w-3 h-3 rounded-full mx-auto mb-2" style={{ backgroundColor: `var(--color-${c.color})` }} />
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatPct(pct)}</p>
                <p className="text-sm font-medium">{c.label}</p>
                <p className="text-xs text-gray-500">{formatNumber(latest[c.key], 3)} km²</p>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}

function LandscapeTab({ stats }: { stats: any[] }) {
  if (stats.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-gray-600 dark:text-gray-400">No statistics available</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-semibold mb-4">Vegetation Patch Metrics (Per Year)</h3>
        <div className="table-container overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left p-3 font-medium">Year</th>
                <th className="text-right p-3 font-medium">Vegetation Area (km²)</th>
                <th className="text-right p-3 font-medium">Vegetation %</th>
                <th className="text-right p-3 font-medium">Valid Coverage %</th>
                <th className="text-right p-3 font-medium">Images Used</th>
              </tr>
            </thead>
            <tbody>
              {stats.map(s => (
                <tr key={s.year} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="p-3 font-medium">{s.year}</td>
                  <td className="p-3 text-right font-mono">{formatNumber(s.vegetation_km2, 3)}</td>
                  <td className="p-3 text-right font-mono">{formatPct(s.vegetation_pct)}</td>
                  <td className="p-3 text-right font-mono">{formatPct(s.quality?.valid_coverage_pct)}</td>
                  <td className="p-3 text-right font-mono">{s.images_used}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Water Body Metrics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Water Area', value: stats[stats.length - 1]?.water_km2, unit: 'km²' },
            { label: 'Water %', value: stats[stats.length - 1]?.water_pct, unit: '%' },
            { label: 'Built-up Area', value: stats[stats.length - 1]?.built_bare_km2, unit: 'km²' },
            { label: 'Built-up %', value: stats[stats.length - 1]?.built_bare_pct, unit: '%' },
          ].map((metric, i) => (
            <div key={i} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {metric.unit === '%' ? formatPct(metric.value) : formatNumber(metric.value, 3)}
              </p>
              <p className="text-sm text-gray-500">{metric.label}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Spectral Indices (Latest Year)</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { label: 'Mean NDVI', value: stats[stats.length - 1]?.mean_ndvi, color: 'green-500' },
            { label: 'Mean MNDWI', value: stats[stats.length - 1]?.mean_mndwi, color: 'blue-500' },
            { label: 'Mean NDBI', value: stats[stats.length - 1]?.mean_ndbi, color: 'amber-500' },
          ].map((metric, i) => (
            <div key={i} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <div className="w-3 h-3 rounded-full mx-auto mb-2" style={{ backgroundColor: `var(--color-${metric.color})` }} />
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{metric.value?.toFixed(3) ?? '—'}</p>
              <p className="text-sm text-gray-500">{metric.label}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

function UrbanGrowthTab({ stats }: { stats: any[] }) {
  if (stats.length < 2) {
    return (
      <Card className="p-8 text-center">
        <BarChart2 className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          Need at least 2 years for growth analysis
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Select multiple years to see built-up growth indicators.
        </p>
      </Card>
    )
  }

  const latest = stats[stats.length - 1]
  const first = stats[0]

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-semibold mb-4">Built-up Area Growth</h3>
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatNumber(first.built_bare_km2, 3)}</p>
              <p className="text-sm text-gray-500">Initial ({first.year})</p>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatNumber(latest.built_bare_km2, 3)}</p>
              <p className="text-sm text-gray-500">Latest ({latest.year})</p>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-red-600">{formatNumber(latest.built_bare_km2 - first.built_bare_km2, 3)}</p>
              <p className="text-sm text-gray-500">Absolute Change</p>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-red-600">
                {first.built_bare_km2 > 0 ? formatPct(((latest.built_bare_km2 - first.built_bare_km2) / first.built_bare_km2) * 100) : '—'}
              </p>
              <p className="text-sm text-gray-500">Relative Change</p>
            </div>
          </div>

          <div className="table-container overflow-x-auto">
            <table className="table w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left p-3 font-medium">Period</th>
                  <th className="text-right p-3 font-medium">Built-up (km²)</th>
                  <th className="text-right p-3 font-medium">Change (km²)</th>
                  <th className="text-right p-3 font-medium">Annual Rate (km²/yr)</th>
                </tr>
              </thead>
              <tbody>
                {stats.slice(1).map((curr, i) => {
                  const prev = stats[i]
                  const change = curr.built_bare_km2 - prev.built_bare_km2
                  const yearsDiff = curr.year - prev.year
                  return (
                    <tr key={curr.year} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="p-3 font-medium">{prev.year} → {curr.year}</td>
                      <td className="p-3 text-right font-mono">{formatNumber(curr.built_bare_km2, 3)}</td>
                      <td className="p-3 text-right font-mono">
                        <span className={change >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {change >= 0 ? '+' : ''}{formatNumber(change, 3)}
                        </span>
                      </td>
                      <td className="p-3 text-right font-mono">
                        {formatNumber(yearsDiff > 0 ? change / yearsDiff : 0, 3)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Expansion Direction & Distance Profile</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Requires backend /api/urban-growth endpoint for rose diagram and distance-from-center analysis.
        </p>
        <div className="aspect-square bg-gray-50 dark:bg-gray-800/50 rounded-lg flex items-center justify-center">
          <span className="text-gray-500">Compass rose visualization (not implemented)</span>
        </div>
      </Card>
    </div>
  )
}

function EnvironmentalTab({ stats }: { stats: any[] }) {
  if (stats.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-gray-600 dark:text-gray-400">No statistics available</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-semibold mb-4">Environmental Correlations</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Requires backend /api/environmental endpoint for LST, NTL, population, and rainfall correlations.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'LST Correlation', icon: '🌡️' },
            { label: 'NTL Correlation', icon: '💡' },
            { label: 'Population Corr.', icon: '👥' },
            { label: 'Rainfall Corr.', icon: '🌧️' },
          ].map((metric, i) => (
            <div key={i} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <p className="text-3xl mb-2">{metric.icon}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">—</p>
              <p className="text-sm text-gray-500">{metric.label}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Available Proxy Data (from analysis)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { label: 'Mean NDVI (Vegetation Health)', value: stats[stats.length - 1]?.mean_ndvi },
            { label: 'Mean MNDWI (Water Index)', value: stats[stats.length - 1]?.mean_mndwi },
            { label: 'Mean NDBI (Built-up Index)', value: stats[stats.length - 1]?.mean_ndbi },
            { label: 'Valid Coverage %', value: stats[stats.length - 1]?.quality?.valid_coverage_pct },
          ].map((metric, i) => (
            <div key={i} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
              <p className="font-medium">{metric.label}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                {metric.value !== undefined ? metric.value.toFixed(3) : '—'}
              </p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

function LakesTab({ stats }: { stats: any[] }) {
  if (stats.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-gray-600 dark:text-gray-400">No statistics available</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-semibold mb-4">Water Body Area Over Time</h3>
        <div className="table-container overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left p-3 font-medium">Year</th>
                <th className="text-right p-3 font-medium">Water Area (km²)</th>
                <th className="text-right p-3 font-medium">Water %</th>
                <th className="text-right p-3 font-medium">Change from Previous (km²)</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((s, i) => {
                const prev = i > 0 ? stats[i - 1] : null
                const change = prev ? s.water_km2 - prev.water_km2 : 0
                return (
                  <tr key={s.year} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="p-3 font-medium">{s.year}</td>
                    <td className="p-3 text-right font-mono">{formatNumber(s.water_km2, 3)}</td>
                    <td className="p-3 text-right font-mono">{formatPct(s.water_pct)}</td>
                    <td className="p-3 text-right font-mono">
                      {i === 0 ? '—' : (
                        <span className={change >= 0 ? 'text-blue-600' : 'text-red-600'}>
                          {change >= 0 ? '+' : ''}{formatNumber(change, 3)}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Water Body Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Current Water Area', value: stats[stats.length - 1]?.water_km2, unit: 'km²' },
            { label: 'Current Water %', value: stats[stats.length - 1]?.water_pct, unit: '%' },
            { label: 'Min Water Area', value: Math.min(...stats.map(s => s.water_km2)), unit: 'km²' },
            { label: 'Max Water Area', value: Math.max(...stats.map(s => s.water_km2)), unit: 'km²' },
          ].map((metric, i) => (
            <div key={i} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {metric.unit === '%' ? formatPct(metric.value) : formatNumber(metric.value, 3)}
              </p>
              <p className="text-sm text-gray-500">{metric.label}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

function HotspotsTab({ stats }: { stats: any[] }) {
  if (stats.length < 2) {
    return (
      <Card className="p-8 text-center">
        <LayoutGrid className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          Need at least 2 years for hotspot analysis
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Select multiple years to identify change hotspots.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-semibold mb-4">Year-over-Year Change Magnitude</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Total absolute land cover change per period (sum of all class changes in km²).
        </p>
        <div className="table-container overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left p-3 font-medium">Period</th>
                <th className="text-right p-3 font-medium">Vegetation Change</th>
                <th className="text-right p-3 font-medium">Water Change</th>
                <th className="text-right p-3 font-medium">Built-up Change</th>
                <th className="text-right p-3 font-medium">Total Absolute Change</th>
              </tr>
            </thead>
            <tbody>
              {stats.slice(1).map((curr, i) => {
                const prev = stats[i]
                const vegChange = Math.abs(curr.vegetation_km2 - prev.vegetation_km2)
                const waterChange = Math.abs(curr.water_km2 - prev.water_km2)
                const builtChange = Math.abs(curr.built_bare_km2 - prev.built_bare_km2)
                const otherChange = Math.abs(curr.other_km2 - prev.other_km2)
                const total = vegChange + waterChange + builtChange + otherChange
                return (
                  <tr key={curr.year} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="p-3 font-medium">{prev.year} → {curr.year}</td>
                    <td className="p-3 text-right font-mono text-green-600">{formatNumber(vegChange, 3)}</td>
                    <td className="p-3 text-right font-mono text-blue-600">{formatNumber(waterChange, 3)}</td>
                    <td className="p-3 text-right font-mono text-amber-600">{formatNumber(builtChange, 3)}</td>
                    <td className="p-3 text-right font-mono font-semibold">{formatNumber(total, 3)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Largest Change Periods</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {['Vegetation Loss', 'Water Gain', 'Built-up Gain'].map((label, idx) => {
            const keyMap = { 'Vegetation Loss': 'vegetation_km2', 'Water Gain': 'water_km2', 'Built-up Gain': 'built_bare_km2' }
            const key = keyMap[label as keyof typeof keyMap]
            // Find max positive change
            let maxChange = 0
            let maxPeriod = ''
            stats.slice(1).forEach((curr, i) => {
              const prev = stats[i]
              const change = curr[key] - prev[key]
              if (change > maxChange) {
                maxChange = change
                maxPeriod = `${prev.year} → ${curr.year}`
              }
            })
            return (
              <div key={label} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <p className="font-medium">{label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                  {maxChange > 0 ? '+' : ''}{formatNumber(maxChange, 3)} km²
                </p>
                <p className="text-sm text-gray-500">{maxPeriod || 'No positive change'}</p>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}