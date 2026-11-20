import React, { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Card } from '../components/ui/Card'
import { FileText, Download, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'

export function ReportPage() {
  const { analysisResult, runAnalysis, isLoading } = useApp()
  const [generating, setGenerating] = useState(false)
  const [reportUrl, setReportUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGenerateReport = async () => {
    if (!analysisResult) return

    setGenerating(true)
    setError(null)
    setReportUrl(null)

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          district_id: analysisResult.district_id,
          years: analysisResult.years,
          season: analysisResult.season,
          classifier: analysisResult.classifier,
          thresholds: analysisResult.thresholds,
          baseline_year: analysisResult.baseline_year,
          include_maps: true,
          title: `Urban Green and Blue Change Report - ${analysisResult.district_id}`,
        }),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Report generation failed')
      }

      const data = await response.json()
      // Assuming base64 PDF response
      const byteCharacters = atob(data.pdf_base64)
      const byteNumbers = new Array(byteCharacters.length)
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i)
      }
      const byteArray = new Uint8Array(byteNumbers)
      const blob = new Blob([byteArray], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      setReportUrl(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Generate Report</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Create a comprehensive PDF report with methodology, charts, maps, and findings.
        </p>
      </div>

      {analysisResult ? (
        <>
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Report Preview</h2>
              <span className="badge badge-info">PDF</span>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">District:</span>
                <span className="font-medium">{analysisResult.district_id || 'Custom Area'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Years:</span>
                <span className="font-medium">{analysisResult.years.join(', ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Season:</span>
                <span className="font-medium">{analysisResult.season.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Classifier:</span>
                <span className="font-medium">{analysisResult.classifier}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Baseline Year:</span>
                <span className="font-medium">{analysisResult.baseline_year || 'Auto'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Scale:</span>
                <span className="font-medium">{analysisResult.scale}m</span>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h3 className="font-medium mb-2">Report Sections</h3>
              <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                <li>• Methodology & Parameters</li>
                <li>• Yearly Statistics Table</li>
                <li>• Land Cover Area Charts</li>
                <li>• Spectral Indices Trends</li>
                <li>• Map Layers (True Color, NDVI, MNDWI, NDBI, Land Cover)</li>
                <li>• Change Maps (Since Baseline, Year-to-Year)</li>
                <li>• Quality Flags & Data Limitations</li>
                <li>• Trend Analysis (if ≥3 years)</li>
                <li>• Accuracy Assessment (if available)</li>
                <li>• Key Findings & Caveats</li>
              </ul>
            </div>
          </Card>

          <div className="flex gap-4">
            <button
              onClick={handleGenerateReport}
              disabled={generating || isLoading}
              className="btn-primary flex-1"
            >
              {generating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Generating…
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Generate PDF Report
                </>
              )}
            </button>

            {reportUrl && (
              <a
                href={reportUrl}
                download={`urban-green-blue-report-${new Date().toISOString().split('T')[0]}.pdf`}
                className="btn-secondary flex-1 flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </a>
            )}
          </div>

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {reportUrl && !generating && (
            <div className="p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2 text-green-700 dark:text-green-400">
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
              <span>Report generated successfully! Click Download to save.</span>
            </div>
          )}
        </>
      ) : (
        <Card className="p-8 text-center">
          <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            No analysis data available
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Run an analysis on the Dashboard first, then return here to generate a report.
          </p>
          <button onClick={runAnalysis} disabled={isLoading} className="btn-primary">
            Go to Dashboard
          </button>
        </Card>
      )}
    </div>
  )
}