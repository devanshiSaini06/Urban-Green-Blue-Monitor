import React from 'react'
import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
}

export function Skeleton({ className, variant = 'text', width, height }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'skeleton',
        variant === 'circular' && 'rounded-full',
        variant === 'rectangular' && 'rounded-lg',
        className
      )}
      style={{ width, height }}
      aria-hidden="true"
    />
  )
}