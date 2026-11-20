import React, { useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { useApp } from '../context/AppContext'
import {
  LayoutDashboard,
  Map,
  BarChart2,
  FileText,
  Settings,
  Sun,
  Moon,
  Menu,
  X,
  Share2,
  Download,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react'
import { clsx } from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Map', href: '/map', icon: Map },
  { name: 'Analysis', href: '/analysis', icon: BarChart2 },
  { name: 'Report', href: '/report', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Layout() {
  const { theme, toggleTheme } = useTheme()
  const { isLoading, runAnalysis, selectedDistrict, districts, analysisResult, error } = useApp()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [shareDialogOpen, setShareDialogOpen] = useState(false)

  const shareUrl = window.location.href

  const copyShareUrl = async () => {
    await navigator.clipboard.writeText(shareUrl)
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-200',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Main navigation"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Urban Green & Blue Monitor
            </h1>
            <button
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Main navigation">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href ||
                (item.href !== '/' && location.pathname.startsWith(item.href))
              return (
                <NavLink
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                  )}
                  aria-current={isActive ? 'page' : undefined}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                  {item.name}
                </NavLink>
              )
            })}
          </nav>

          {/* District selector & controls */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
            <div>
              <label className="label" htmlFor="district-select">District</label>
              <select
                id="district-select"
                className="input"
                value={selectedDistrict}
                onChange={(e) => {
                  const district = districts.find(d => d.id === e.target.value)
                  if (district) window.location.href = `/?district=${district.id}`
                }}
              >
                {districts.map(d => (
                  <option key={d.id} value={d.id}>{d.display_name}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={runAnalysis}
                disabled={isLoading}
                className="btn-primary flex-1"
                aria-busy={isLoading}
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin mr-2" aria-hidden="true" />
                    Running...
                  </>
                ) : (
                  'Run Analysis'
                )}
              </button>
              <button
                onClick={() => setShareDialogOpen(true)}
                className="btn-secondary"
                aria-label="Share current view"
              >
                <Share2 className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>

            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}

            {analysisResult?.quality_summary && (
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg text-sm text-yellow-800 dark:text-yellow-400">
                <p className="font-medium mb-1">Data Quality Notes:</p>
                <ul className="list-disc list-inside space-y-1">
                  {analysisResult.quality_summary.years_with_warnings > 0 && (
                    <li>{analysisResult.quality_summary.years_with_warnings} year(s) with low image count or coverage</li>
                  )}
                  {analysisResult.quality_summary.outlier_years.length > 0 && (
                    <li>Outlier detected in: {analysisResult.quality_summary.outlier_years.join(', ')}</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 lg:ml-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between h-16 px-4">
            <button
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu className="w-6 h-6" aria-hidden="true" />
            </button>

            <div className="flex-1 lg:flex-none text-center lg:text-left">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {navigation.find(n => location.pathname === n.href || location.pathname.startsWith(n.href))?.name || 'Dashboard'}
              </h2>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              >
                {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          <Outlet />
        </main>
      </div>

      {/* Share dialog */}
      {shareDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShareDialogOpen(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">Share Current View</h3>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={shareUrl}
                readOnly
                className="input flex-1"
              />
              <button
                onClick={copyShareUrl}
                className="btn-secondary"
              >
                Copy
              </button>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              This link captures all current settings: district, years, season, classifier, thresholds, and map view.
            </p>
            <button
              onClick={() => setShareDialogOpen(false)}
              className="btn-primary w-full"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}