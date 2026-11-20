import React, { useEffect, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ArcElement,
} from 'chart.js'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import { Card } from './ui/Card'
import { clsx } from 'clsx'
import { YearlyStats } from '../context/AppContext'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ArcElement
)

const COLORS = {
  vegetation: 'rgb(34, 197, 94)',
  water: 'rgb(14, 165, 233)',
  built: 'rgb(115, 115, 115)',
  other: 'rgb(161, 161, 170)',
  ndvi: 'rgb(21, 128, 61)',
  mndwi: 'rgb(2, 132, 199)',
  ndbi: 'rgb(82, 82, 82)',
}

interface ChartsProps {
  stats: YearlyStats[]
  baselineYear: number | null
}

export function Charts({ stats, baselineYear }: ChartsProps) {
  // Sort stats by year
  const sortedStats = [...stats].sort((a, b) => a.year - b.year)
  const years = sortedStats.map(s => s.year)
  const labels = years.map(y => String(y))

  // Chart data
  const areaData = {
    labels,
    datasets: [
      {
        label: 'Vegetation',
        data: sortedStats.map(s => s.vegetation_km2),
        borderColor: COLORS.vegetation,
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Water',
        data: sortedStats.map(s => s.water_km2),
        borderColor: COLORS.water,
        backgroundColor: 'rgba(14, 165, 233, 0.1)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Built-up/Bare',
        data: sortedStats.map(s => s.built_bare_km2),
        borderColor: COLORS.built,
        backgroundColor: 'rgba(115, 115, 115, 0.1)',
        fill: true,
        tension: 0.3,
      },
    ],
  }

  const shareData = {
    labels,
    datasets: [
      {
        label: 'Vegetation %',
        data: sortedStats.map(s => s.vegetation_pct),
        borderColor: COLORS.vegetation,
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Water %',
        data: sortedStats.map(s => s.water_pct),
        borderColor: COLORS.water,
        backgroundColor: 'rgba(14, 165, 233, 0.1)',
        fill: true,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Built-up/Bare %',
        data: sortedStats.map(s => s.built_bare_pct),
        borderColor: COLORS.built,
        backgroundColor: 'rgba(115, 115, 115, 0.1)',
        fill: true,
        tension: 0.3,
        yAxisID: 'y',
      },
    ],
  }

  const indexData = {
    labels,
    datasets: [
      {
        label: 'Mean NDVI',
        data: sortedStats.map(s => s.mean_ndvi),
        borderColor: COLORS.ndvi,
        backgroundColor: 'rgba(21, 128, 61, 0.1)',
        fill: false,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Mean MNDWI',
        data: sortedStats.map(s => s.mean_mndwi),
        borderColor: COLORS.mndwi,
        backgroundColor: 'rgba(2, 132, 199, 0.1)',
        fill: false,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Mean NDBI',
        data: sortedStats.map(s => s.mean_ndbi),
        borderColor: COLORS.ndbi,
        backgroundColor: 'rgba(82, 82, 82, 0.1)',
        fill: false,
        tension: 0.3,
        yAxisID: 'y',
      },
    ],
  }

  // Normalized data (baseline = 100)
  const normalizedData = (() => {
    if (!baselineYear) return null
    const baselineStats = sortedStats.find(s => s.year === baselineYear)
    if (!baselineStats) return null

    const baselineValues = {
      vegetation: baselineStats.vegetation_km2,
      water: baselineStats.water_km2,
      built: baselineStats.built_bare_km2,
      vegetation_pct: baselineStats.vegetation_pct,
      water_pct: baselineStats.water_pct,
      built_pct: baselineStats.built_bare_pct,
      ndvi: baselineStats.mean_ndvi,
      mndwi: baselineStats.mean_mndwi,
      ndbi: baselineStats.mean_ndbi,
    }

    return {
      labels,
      datasets: [
        {
          label: 'Vegetation (norm.)',
          data: sortedStats.map(s => baselineValues.vegetation > 0 ? (s.vegetation_km2 / baselineValues.vegetation) * 100 : 100),
          borderColor: COLORS.vegetation,
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          fill: true,
          tension: 0.3,
        },
        {
          label: 'Water (norm.)',
          data: sortedStats.map(s => baselineValues.water > 0 ? (s.water_km2 / baselineValues.water) * 100 : 100),
          borderColor: COLORS.water,
          backgroundColor: 'rgba(14, 165, 233, 0.1)',
          fill: true,
          tension: 0.3,
        },
        {
          label: 'Built-up/Bare (norm.)',
          data: sortedStats.map(s => baselineValues.built > 0 ? (s.built_bare_km2 / baselineValues.built) * 100 : 100),
          borderColor: COLORS.built,
          backgroundColor: 'rgba(115, 115, 115, 0.1)',
          fill: true,
          tension: 0.3,
        },
      ],
    }
  })()

  // Stacked composition
  const compositionData = {
    labels,
    datasets: [
      {
        label: 'Vegetation',
        data: sortedStats.map(s => s.vegetation_pct),
        backgroundColor: COLORS.vegetation,
      },
      {
        label: 'Water',
        data: sortedStats.map(s => s.water_pct),
        backgroundColor: COLORS.water,
      },
      {
        label: 'Built-up/Bare',
        data: sortedStats.map(s => s.built_bare_pct),
        backgroundColor: COLORS.built,
      },
      {
        label: 'Other',
        data: sortedStats.map(s => s.other_pct),
        backgroundColor: COLORS.other,
      },
    ],
  }

  // Quality data
  const qualityData = {
    labels,
    datasets: [
      {
        label: 'Images Used',
        data: sortedStats.map(s => s.images_used),
        borderColor: 'rgb(107, 114, 128)',
        backgroundColor: 'rgba(107, 114, 128, 0.1)',
        fill: false,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Valid Coverage %',
        data: sortedStats.map(s => s.quality.valid_coverage_pct),
        borderColor: 'rgb(234, 179, 8)',
        backgroundColor: 'rgba(234, 179, 8, 0.1)',
        fill: false,
        tension: 0.3,
        yAxisID: 'y1',
        type: 'line',
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          usePointStyle: true,
          padding: 16,
          font: { size: 11 },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(17, 24, 39, 0.9)',
        titleFont: { size: 12 },
        bodyFont: { size: 11 },
        padding: 10,
        cornerRadius: 6,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { size: 11 } },
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: { font: { size: 11 } },
      },
    },
  }

  const dualAxisOptions = {
    ...chartOptions,
    scales: {
      x: chartOptions.scales.x,
      y: {
        ...chartOptions.scales.y,
        position: 'left' as const,
      },
      y1: {
        beginAtZero: true,
        position: 'right' as const,
        grid: { drawOnChartArea: false },
        ticks: { font: { size: 11 } },
      },
    },
  }

  return (
    <div className="space-y-6">
      {/* Area chart */}
      <Card>
        <Line
          data={areaData}
          options={{
            ...chartOptions,
            plugins: {
              ...chartOptions.plugins,
              title: {
                display: true,
                text: 'Land Cover Area Over Time (km²)',
                font: { size: 14, weight: '600' },
              },
            },
          }}
        />
      </Card>

      {/* Share chart */}
      <Card>
        <Line
          data={shareData}
          options={{
            ...chartOptions,
            scales: {
              ...chartOptions.scales,
              y: { ...chartOptions.scales.y, max: 100, title: { display: true, text: 'Percentage (%)' } },
            },
            plugins: {
              ...chartOptions.plugins,
              title: {
                display: true,
                text: 'Land Cover Share Over Time (%)',
                font: { size: 14, weight: '600' },
              },
            },
          }}
        />
      </Card>

      {/* Indices chart */}
      <Card>
        <Line
          data={indexData}
          options={{
            ...dualAxisOptions,
            plugins: {
              ...chartOptions.plugins,
              title: {
                display: true,
                text: 'Spectral Indices Over Time',
                font: { size: 14, weight: '600' },
              },
            },
          }}
        />
      </Card>

      {/* Normalized chart */}
      {normalizedData && (
        <Card>
          <Line
            data={normalizedData}
            options={{
              ...chartOptions,
              scales: {
                ...chartOptions.scales,
                y: { ...chartOptions.scales.y, min: 0, title: { display: true, text: 'Index (Baseline = 100)' } },
              },
              plugins: {
                ...chartOptions.plugins,
                title: {
                  display: true,
                  text: `Normalized Change (${baselineYear} = 100)`,
                  font: { size: 14, weight: '600' },
                },
              },
            }}
          />
        </Card>
      )}

      {/* Stacked composition */}
      <Card>
        <Bar
          data={compositionData}
          options={{
            ...chartOptions,
            plugins: {
              ...chartOptions.plugins,
              title: {
                display: true,
                text: 'Stacked Land Cover Composition (%)',
                font: { size: 14, weight: '600' },
              },
            },
            scales: {
              ...chartOptions.scales,
              x: { ...chartOptions.scales.x, stacked: true },
              y: { ...chartOptions.scales.y, stacked: true, max: 100 },
            },
          }}
        />
      </Card>

      {/* Quality chart */}
      <Card>
        <Bar
          data={qualityData}
          options={{
            ...dualAxisOptions,
            plugins: {
              ...chartOptions.plugins,
              title: {
                display: true,
                text: 'Data Quality: Images Used & Valid Coverage',
                font: { size: 14, weight: '600' },
              },
            },
          }}
        />
      </Card>
    </div>
  )
}