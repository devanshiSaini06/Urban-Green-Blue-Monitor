import React, { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Calendar, ChevronDown } from 'lucide-react'
import { clsx } from 'clsx'
import { SeasonWindow } from '../context/AppContext'

const SEASON_OPTIONS = [
  { value: 'oct-dec', label: 'Oct–Dec (Post-monsoon)', months: 'Oct–Dec' },
  { value: 'jan-mar', label: 'Jan–Mar (Winter)', months: 'Jan–Mar' },
  { value: 'mar-may', label: 'Mar–May (Pre-monsoon)', months: 'Mar–May' },
  { value: 'jun-sep', label: 'Jun–Sep (Monsoon)', months: 'Jun–Sep' },
] as const

export function SeasonSelector() {
  const { season, setSeason } = useApp()
  const [isCustom, setIsCustom] = useState(false)
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')

  const handleSeasonChange = (name: SeasonWindow['name']) => {
    if (name === 'custom') {
      setIsCustom(true)
      return
    }
    setIsCustom(false)
    const option = SEASON_OPTIONS.find(o => o.value === name)
    if (option) {
      setSeason({
        name,
        start_month: name === 'oct-dec' ? 10 : parseInt(name.split('-')[0]),
        end_month: name === 'oct-dec' ? 1 : parseInt(name.split('-')[1]) + 1,
        custom_start: null,
        custom_end: null,
      })
    }
  }

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (customStart && customEnd) {
      setSeason({
        name: 'custom',
        start_month: null,
        end_month: null,
        custom_start: customStart,
        custom_end: customEnd,
      })
      setIsCustom(false)
    }
  }

  return (
    <div className="relative">
      <label className="label" htmlId="season-select">Season</label>

      {!isCustom ? (
        <div className="relative">
          <select
            id="season-select"
            className="input pr-10 appearance-none"
            value={season.name}
            onChange={e => handleSeasonChange(e.target.value as SeasonWindow['name'])}
          >
            {SEASON_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
            <option value="custom">Custom date range…</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" aria-hidden="true" />
        </div>
      ) : (
        <form onSubmit={handleCustomSubmit} className="flex items-center gap-2">
          <input
            type="date"
            value={customStart}
            onChange={e => setCustomStart(e.target.value)}
            className="input flex-1"
            placeholder="Start date"
            required
          />
          <span className="text-gray-400">to</span>
          <input
            type="date"
            value={customEnd}
            onChange={e => setCustomEnd(e.target.value)}
            className="input flex-1"
            placeholder="End date"
            required
          />
          <button type="submit" className="btn-primary btn-sm">Apply</button>
          <button
            type="button"
            onClick={() => setIsCustom(false)}
            className="btn-ghost btn-sm"
            aria-label="Cancel custom season"
          >
            <Calendar className="w-4 h-4" aria-hidden="true" />
          </button>
        </form>
      )}

      {season.name !== 'oct-dec' && (
        <div className="mt-1 text-xs text-yellow-600 dark:text-yellow-400 flex items-center gap-1">
          <span>⚠</span>
          <span>Comparing years with different seasons may affect results</span>
        </div>
      )}
    </div>
  )
}