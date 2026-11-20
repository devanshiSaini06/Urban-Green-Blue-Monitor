import React, { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { Download, ChevronUp, ChevronDown, FileText, Table as TableIcon } from 'lucide-react'
import { Card } from './ui/Card'
import { YearlyStats, QualitySummary } from '../context/AppContext'
import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'

interface DataTableProps {
  stats: YearlyStats[]
  qualitySummary?: QualitySummary
}

const COLUMNS = [
  { key: 'year', label: 'Year', type: 'number' as const },
  { key: 'images_used', label: 'Images', type: 'number' as const },
  { key: 'valid_coverage_pct', label: 'Coverage %', type: 'number', format: (v: number) => v.toFixed(1) },
  { key: 'vegetation_km2', label: 'Veg. km²', type: 'number', format: (v: number) => v.toFixed(2) },
  { key: 'vegetation_pct', label: 'Veg. %', type: 'number', format: (v: number) => v.toFixed(1) },
  { key: 'water_km2', label: 'Water km²', type: 'number', format: (v: number) => v.toFixed(2) },
  { key: 'water_pct', label: 'Water %', type: 'number', format: (v: number) => v.toFixed(1) },
  { key: 'built_bare_km2', label: 'Built km²', type: 'number', format: (v: number) => v.toFixed(2) },
  { key: 'built_bare_pct', label: 'Built %', type: 'number', format: (v: number) => v.toFixed(1) },
  { key: 'other_km2', label: 'Other km²', type: 'number', format: (v: number) => v.toFixed(2) },
  { key: 'mean_ndvi', label: 'Mean NDVI', type: 'number', format: (v: number) => v.toFixed(3) },
  { key: 'mean_mndwi', label: 'Mean MNDWI', type: 'number', format: (v: number) => v.toFixed(3) },
  { key: 'mean_ndbi', label: 'Mean NDBI', type: 'number', format: (v: number) => v.toFixed(3) },
  { key: 'quality_flags', label: 'Quality', type: 'custom' as const },
] as const

type SortDirection = 'asc' | 'desc' | null

export function DataTable({ stats, qualitySummary }: DataTableProps) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: SortDirection }>({ key: 'year', direction: 'asc' })

  const sortedStats = useMemo(() => {
    const { key, direction } = sortConfig
    if (!direction) return stats

    return [...stats].sort((a, b) => {
      const aVal = (a as any)[key]
      const bVal = (b as any)[key]

      if (aVal === undefined || bVal === undefined) return 0

      if (typeof aVal === 'string') {
        return direction === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      return direction === 'asc' ? aVal - bVal : bVal - aVal
    })
  }, [stats, sortConfig])

  const handleSort = (key: string) => {
    setSortConfig(current => ({
      key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const getQualityBadge = (quality: YearlyStats['quality']) => {
    const flags = []
    if (quality.low_image_count) flags.push('Low images')
    if (quality.low_coverage) flags.push('Low coverage')
    if (quality.outlier_flag) flags.push('Outlier')
    return flags.length > 0 ? flags.join(', ') : 'OK'
  }

  const getQualityBadgeClass = (quality: YearlyStats['quality']) => {
    if (quality.outlier_flag) return 'badge-danger'
    if (quality.low_image_count || quality.low_coverage) return 'badge-warning'
    return 'badge-success'
  }

  const exportCSV = () => {
    const headers = COLUMNS.map(c => c.label)
    const rows = sortedStats.map(stat =>
      COLUMNS.map(col => {
        const value = (stat as any)[col.key]
        if (col.key === 'quality_flags') return getQualityBadge(stat.quality)
        if (col.format && typeof value === 'number') return col.format(value)
        return value
      })
    )
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    saveAs(blob, `land-cover-stats-${new Date().toISOString().split('T')[0]}.csv`)
  }

  const exportExcel = () => {
    const wsData = [
      COLUMNS.map(c => c.label),
      ...sortedStats.map(stat =>
        COLUMNS.map(col => {
          const value = (stat as any)[col.key]
          if (col.key === 'quality_flags') return getQualityBadge(stat.quality)
          if (col.format && typeof value === 'number') return col.format(value)
          return value
        })
      ),
    ]
    const ws = XLSX.utils.aoa_to_sheet(wsData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Land Cover Stats')
    XLSX.writeFile(wb, `land-cover-stats-${new Date().toISOString().split('T')[0]}.xlsx`)
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Yearly Statistics</h3>
        <div className="flex items-center gap-2">
          <button onClick={exportCSV} className="btn-secondary btn-sm" aria-label="Export as CSV">
            <Download className="w-4 h-4 mr-1" aria-hidden="true" />
            CSV
          </button>
          <button onClick={exportExcel} className="btn-secondary btn-sm" aria-label="Export as Excel">
            <FileText className="w-4 h-4 mr-1" aria-hidden="true" />
            Excel
          </button>
        </div>
      </div>

      <div className="table-container">
        <table className="table" role="grid">
          <thead>
            <tr>
              {COLUMNS.map(col => (
                <th
                  key={col.key}
                  scope="col"
                  className={clsx('cursor-pointer select-none', col.type === 'custom' && 'w-32')}
                  onClick={() => col.type !== 'custom' && handleSort(col.key)}
                  aria-sort={sortConfig.key === col.key ? (sortConfig.direction === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {col.type !== 'custom' && sortConfig.key === col.key && (
                      sortConfig.direction === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedStats.map(stat => (
              <tr key={stat.year}>
                {COLUMNS.map(col => {
                  const value = (stat as any)[col.key]
                  if (col.key === 'quality_flags') {
                    return (
                      <td key={col.key}>
                        <span className={clsx('badge', getQualityBadgeClass(stat.quality))}>
                          {getQualityBadge(stat.quality)}
                        </span>
                      </td>
                    )
                  }
                  return (
                    <td key={col.key}>
                      {col.format && typeof value === 'number' ? col.format(value) : value}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {qualitySummary && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Quality Summary</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Years with warnings: </span>
              <span className="font-medium">{qualitySummary.years_with_warnings}</span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Outlier years: </span>
              <span className="font-medium">{qualitySummary.outlier_years.join(', ') || 'None'}</span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Recommended baseline: </span>
              <span className="font-medium">{qualitySummary.best_quality_year}</span>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}