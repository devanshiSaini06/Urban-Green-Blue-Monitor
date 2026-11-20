import React from 'react'
import { Link } from 'react-router-dom'
import { Home, Search } from 'lucide-react'
import { Card } from '../components/ui/Card'

export function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="p-8 text-center max-w-md">
        <div className="text-6xl font-bold text-primary-600 mb-4">404</div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Page Not Found
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex gap-3 justify-center">
          <Link to="/" className="btn-primary">
            <Home className="w-4 h-4 mr-2" />
            Go Home
          </Link>
        </div>
      </Card>
    </div>
  )
}