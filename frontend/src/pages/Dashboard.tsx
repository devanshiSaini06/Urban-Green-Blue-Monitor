import React, { useMemo } from 'react'
import { useApp } from '../context/AppContext'
import { KPICards } from '../components/KPICards'
import { Charts } from '../components/Charts'
import { DataTable } from '../components/DataTable'
import { YearSelector } from '../components/YearSelector'
import { SeasonSelector } from '../components/SeasonSelector'
import { ClassifierSelector } from '../components/ClassifierSelector'
import { ThresholdSliders } from '../components/ThresholdSliders'
import { Card } from '../components/ui/Card'
import { Skeleton } from '../components/ui/Skeleton'

export function Dashboard() {
  const { analysisResult, isLoading, selectedYears, runAnalysis, districts, selectedDistrict } = useApp()

  const district = districts.find(d => d.id === selectedDistrict)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-4 w-1/4 mb-2" />
              <Skeleton className="h-8 w-1/2" />
              <Skeleton className="h-4 w-1/3 mt-2" />
            </Card>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6"><Skeleton className="h-64 w-full" /></Card>
          <Card className="p-6"><Skeleton className="h-64 w-full" /></Card>
        </div>
        <Card className="p-6"><Skeleton className="h-96 w-full" /></Card>
      </div>
    )
  }

  if (!analysisResult) {
    return (
      <div className="text-center py-12">
        <div className="max-w-md mx-auto">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Welcome to Urban Green & Blue Change Monitor
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Select a district and years, then click "Run Analysis" to compare vegetation, surface water,
            and built-up land changes between 2018 and 2025.
          </p>
          <div className="space-y-4">
            <YearSelector />
            <SeasonSelector />
            <ClassifierSelector />
            <ThresholdSliders />
          </div>
        </div>
      </div>
    )
  }

  // Get stats for first and last selected year for comparison
  const firstYear = selectedYears[0]
  const lastYear = selectedYears[selectedYears.length - 1]

  const firstStats = analysisResult.stats.find(s => s.year === firstYear)
  const lastStats = analysisResult.stats.find(s => s.year === lastYear)

  const hasComparison = firstStats && lastStats && firstYear !== lastYear

  return (
    <div className="space-y-6">
      {/* Header with controls */}
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {district?.display_name || 'Custom Area'}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {analysisResult.classifier === 'spectral' ? 'Spectral Rules' : 'Dynamic World'} Classifier •
            {analysisResult.season.name} • Scale: {analysisResult.scale}m
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <YearSelector />
          <SeasonSelector />
          <ClassifierSelector />
        </div>
      </div>

      {/* KPI Cards */}
      <KPICards
        firstStats={firstStats}
        lastStats={lastStats}
        hasComparison={hasComparison}
        firstYear={firstYear}
        lastYear={lastYear}
      />

      {/* Threshold sliders (collapsible) */}
      <ThresholdSliders />

      {/* Charts */}
      <Charts stats={analysisResult.stats} baselineYear={analysisResult.baseline_year} />

      {/* Data Table */}
      <DataTable stats={analysisResult.stats} qualitySummary={analysisResult.quality_summary} />
    </div>
  )
}