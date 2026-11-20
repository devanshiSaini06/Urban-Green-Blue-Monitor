import React from 'react'
import { useApp } from '../context/AppContext'
import { clsx } from 'clsx'
import { Layers, Brain } from 'lucide-react'

export function ClassifierSelector() {
  const { classifier, setClassifier } = useApp()

  return (
    <div className="flex items-center gap-2">
      <label className="label" htmlId="classifier-select">Classifier</label>
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1" role="radiogroup" aria-label="Select classifier">
        <button
          role="radio"
          aria-checked={classifier === 'spectral'}
          onClick={() => setClassifier('spectral')}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
            classifier === 'spectral'
              ? 'bg-white text-primary-700 shadow-sm dark:bg-gray-600 dark:text-primary-300'
              : 'text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100'
          )}
        >
          <Layers className="w-4 h-4" aria-hidden="true" />
          Spectral
        </button>
        <button
          role="radio"
          aria-checked={classifier === 'dynamic_world'}
          onClick={() => setClassifier('dynamic_world')}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
            classifier === 'dynamic_world'
              ? 'bg-white text-primary-700 shadow-sm dark:bg-gray-600 dark:text-primary-300'
              : 'text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100'
          )}
        >
          <Brain className="w-4 h-4" aria-hidden="true" />
          Dynamic World
        </button>
      </div>
    </div>
  )
}