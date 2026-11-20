import React from 'react'
import { useTheme } from '../context/ThemeContext'
import { useApp } from '../context/AppContext'
import { Card } from '../components/ui/Card'
import { Sun, Moon, Monitor, Database, RefreshCw, Trash2, Info, AlertTriangle } from 'lucide-react'
import { clsx } from 'clsx'

export function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { resetToDefaults, analysisResult, runAnalysis } = useApp()
  const [cacheStats, setCacheStats] = React.useState<{ total: number; size: string } | null>(null)

  const fetchCacheStats = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/cache/stats`)
      if (response.ok) {
        const data = await response.json()
        setCacheStats({ total: data.active_entries, size: `${data.size_mb} MB` })
      }
    } catch (err) {
      console.error('Failed to fetch cache stats:', err)
    }
  }

  const clearCache = async () => {
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/api/cache/clear`, { method: 'POST' })
      fetchCacheStats()
    } catch (err) {
      console.error('Failed to clear cache:', err)
    }
  }

  React.useEffect(() => {
    fetchCacheStats()
  }, [])

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Configure application preferences and manage data.
        </p>
      </div>

      {/* Appearance */}
      <Card>
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Monitor className="w-5 h-5" />
          Appearance
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(['light', 'dark', 'system'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setTheme(mode === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : mode)}
              className={clsx(
                'p-4 rounded-lg border-2 transition-colors flex flex-col items-center gap-2',
                theme === mode || (mode === 'system' && !['light', 'dark'].includes(theme))
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              )}
            >
              {mode === 'light' && <Sun className="w-6 h-6" />}
              {mode === 'dark' && <Moon className="w-6 h-6" />}
              {mode === 'system' && <Monitor className="w-6 h-6" />}
              <span className="font-medium capitalize">{mode}</span>
            </button>
          ))}
        </div>
      </Card>

      {/* Cache Management */}
      <Card>
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Database className="w-5 h-5" />
          Cache Management
        </h2>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4 text-sm">
            <span className="text-gray-500">Entries:</span>
            <span className="font-medium">{cacheStats?.total ?? '—'}</span>
            <span className="text-gray-500">Size:</span>
            <span className="font-medium">{cacheStats?.size ?? '—'}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchCacheStats}
              className="btn-secondary btn-sm"
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              Refresh
            </button>
            <button
              onClick={clearCache}
              className="btn-secondary btn-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Clear Cache
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          Cached analysis results are stored for 30 days. Clearing the cache will force fresh
          computations on next analysis run.
        </p>
      </Card>

      {/* Data & Analysis */}
      <Card>
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Info className="w-5 h-5" />
          Study Configuration
        </h2>
        <dl className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <dt className="text-gray-500">Study Period</dt>
            <dd className="font-medium">2018–2025 (8 years, fixed)</dd>
            <dt className="text-gray-500">Default Season</dt>
            <dd className="font-medium">Oct–Dec (Post-monsoon)</dd>
            <dt className="text-gray-500">Default Scale</dt>
            <dd className="font-medium">20 meters</dd>
            <dt className="text-gray-500">Projection</dt>
            <dd className="font-medium">EPSG:32643 (UTM Zone 43N)</dd>
            <dt className="text-gray-500">Cloud Threshold</dt>
            <dd className="font-medium">{'< 80%'}</dd>
            <dt className="text-gray-500">Districts</dt>
            <dd className="font-medium">Bengaluru Urban, Gautam Buddha Nagar</dd>
          </div>
        </dl>
      </Card>

      {/* About / Version */}
      <Card>
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          Important Notes
        </h2>
        <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li className="flex items-start gap-2">
            <span className="text-primary-600 mt-0.5">•</span>
            <span>2018 data may have lower image count due to Sentinel-2 coverage limitations over India.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-600 mt-0.5">•</span>
            <span>Built-up class from spectral rules includes bare soil; use Dynamic World for comparison.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-600 mt-0.5">•</span>
            <span>Trend analysis with n=8 has very low statistical power; interpret with caution.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-600 mt-0.5">•</span>
            <span>WorldCover validation only available for 2020 (v100) and 2021 (v200).</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-600 mt-0.5">•</span>
            <span>All threshold values are adjustable; results are sensitive to threshold choices.</span>
          </li>
        </ul>
      </Card>

      {/* Reset */}
      <Card className="border-red-200 dark:border-red-800">
        <h2 className="font-semibold mb-4 flex items-center gap-2 text-red-600">
          <Trash2 className="w-5 h-5" />
          Reset Application
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Reset all settings to defaults and clear current analysis results.
        </p>
        <button
          onClick={resetToDefaults}
          className="btn-secondary text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 border-red-200 dark:border-red-800"
        >
          Reset to Defaults
        </button>
      </Card>
    </div>
  )
}