import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { MapView } from './pages/MapView'
import { AnalysisPage } from './pages/AnalysisPage'
import { ReportPage } from './pages/ReportPage'
import { SettingsPage } from './pages/SettingsPage'
import { NotFound } from './pages/NotFound'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="map" element={<MapView />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="report" element={<ReportPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App