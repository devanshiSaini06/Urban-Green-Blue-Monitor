import React from 'react'
import { useApp } from '../context/AppContext'
import { clsx } from 'clsx'

const STUDY_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

export function YearSelector() {
  const { selectedYears, setYears } = useApp()

  const toggleYear = (year: number) => {
    const newYears = selectedYears.includes(year)
      ? selectedYears.filter(y => y !== year)
      : [...selectedYears, year].sort((a, b) => a - b)
    setYears(newYears)
  }

  return (
    <div className="flex items-center gap-2">
      <label className="label" htmlId="year-select">Years</label>
      <div className="flex flex-wrap gap-1" role="group" aria-label="Select years">
        {STUDY_YEARS.map(year => (
          <button
            key={year}
            type="button"
            onClick={() => toggleYear(year)}
            className={clsx(
              'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors min-w-[3.5rem]',
              selectedYears.includes(year)
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            )}
            aria-pressed={selectedYears.includes(year)}
          >
            {year}
          </button>
        ))}
      </div>
      {selectedYears.length > 0 && (
        <button
          onClick={() => setYears([])}
          className="text-sm text-primary-600 hover:underline"
          aria-label="Clear all years"
        >
          Clear
        </button>
      )}
    </div>
  )
}