import { render, screen } from '@testing-library/react'
import { KPICards } from '../KPICards'
import { AppProvider } from '../../context/AppContext'
import { ThemeProvider } from '../../context/ThemeContext'
import { MemoryRouter } from 'react-router-dom'
import { YearlyStats, QualityFlags } from '../../context/AppContext'

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <AppProvider>
          {component}
        </AppProvider>
      </ThemeProvider>
    </MemoryRouter>
  )
}

const mockFirstStats: YearlyStats = {
  year: 2018,
  images_used: 10,
  valid_km2: 200,
  vegetation_km2: 50,
  water_km2: 10,
  built_bare_km2: 30,
  other_km2: 110,
  vegetation_pct: 25,
  water_pct: 5,
  built_bare_pct: 15,
  other_pct: 55,
  mean_ndvi: 0.3,
  mean_mndwi: -0.1,
  mean_ndbi: 0.05,
  composite_first_date: '2018-10-15',
  composite_last_date: '2018-12-20',
  quality: {
    low_image_count: false,
    low_coverage: false,
    outlier_flag: false,
    outlier_details: null,
    images_used: 10,
    valid_coverage_pct: 90,
  },
  raw_district_km2: 220,
}

const mockLastStats: YearlyStats = {
  ...mockFirstStats,
  year: 2025,
  images_used: 20,
  valid_km2: 205,
  vegetation_km2: 55,
  water_km2: 12,
  built_bare_km2: 40,
  other_km2: 98,
  vegetation_pct: 26.8,
  water_pct: 5.9,
  built_bare_pct: 19.5,
  other_pct: 47.8,
  mean_ndvi: 0.35,
  mean_mndwi: -0.08,
  mean_ndbi: 0.08,
  quality: {
    low_image_count: false,
    low_coverage: false,
    outlier_flag: false,
    outlier_details: null,
    images_used: 20,
    valid_coverage_pct: 92,
  },
}

describe('KPICards', () => {
  it('renders comparison when two different years selected', () => {
    renderWithProviders(
      <KPICards
        firstStats={mockFirstStats}
        lastStats={mockLastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    expect(screen.getByText('Vegetation (2018→2025)')).toBeInTheDocument()
    expect(screen.getByText('Water (2018→2025)')).toBeInTheDocument()
    expect(screen.getByText('Built-up/Bare (2018→2025)')).toBeInTheDocument()
    expect(screen.getByText('Mean NDVI (2018→2025)')).toBeInTheDocument()
  })

  it('shows correct values for vegetation change', () => {
    renderWithProviders(
      <KPICards
        firstStats={mockFirstStats}
        lastStats={mockLastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    // Vegetation: 50 -> 55 km², +5 km², +10%
    expect(screen.getByText('55.00')).toBeInTheDocument()
    expect(screen.getByText('+10.0%')).toBeInTheDocument()
    expect(screen.getByText('(+5.00 km²)')).toBeInTheDocument()
  })

  it('shows correct values for water change', () => {
    renderWithProviders(
      <KPICards
        firstStats={mockFirstStats}
        lastStats={mockLastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    // Water: 10 -> 12 km², +2 km², +20%
    expect(screen.getByText('12.00')).toBeInTheDocument()
  })

  it('shows correct values for built-up change', () => {
    renderWithProviders(
      <KPICards
        firstStats={mockFirstStats}
        lastStats={mockLastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    // Built: 30 -> 40 km², +10 km², +33.3%
    expect(screen.getByText('40.00')).toBeInTheDocument()
  })

  it('shows correct values for NDVI change', () => {
    renderWithProviders(
      <KPICards
        firstStats={mockFirstStats}
        lastStats={mockLastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    // NDVI: 0.3 -> 0.35, +0.05
    expect(screen.getByText('0.350')).toBeInTheDocument()
  })

  it('shows gain in green for positive changes', () => {
    renderWithProviders(
      <KPICards
        firstStats={mockFirstStats}
        lastStats={mockLastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    // Vegetation gain should be green
    const vegCard = screen.getByText('Vegetation (2018→2025)').closest('.card')
    expect(vegCard).toHaveClass('text-green-600')
  })

  it('shows loss in red for negative changes', () => {
    // Create stats where vegetation decreases
    const firstStats = { ...mockFirstStats, vegetation_km2: 60, vegetation_pct: 30 }
    const lastStats = { ...mockLastStats, vegetation_km2: 50, vegetation_pct: 24.4 }

    renderWithProviders(
      <KPICards
        firstStats={firstStats}
        lastStats={lastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    // Should show negative change in red
    expect(screen.getByText(/-16.7%/)).toBeInTheDocument()
  })

  it('shows message when no comparison available', () => {
    renderWithProviders(
      <KPICards
        firstStats={undefined}
        lastStats={undefined}
        hasComparison={false}
        firstYear={2018}
        lastYear={2025}
      />
    )

    expect(screen.getByText('Select two different years to see change comparison')).toBeInTheDocument()
  })

  it('shows quality warning badge when low image count', () => {
    const firstStats = { ...mockFirstStats }
    const lastStats = {
      ...mockLastStats,
      quality: {
        low_image_count: true,
        low_coverage: false,
        outlier_flag: false,
        outlier_details: null,
        images_used: 3,
        valid_coverage_pct: 90,
      },
    }

    renderWithProviders(
      <KPICards
        firstStats={firstStats}
        lastStats={lastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    expect(screen.getByText('Low images (3)')).toBeInTheDocument()
  })

  it('shows quality warning badge when low coverage', () => {
    const firstStats = { ...mockFirstStats }
    const lastStats = {
      ...mockLastStats,
      quality: {
        low_image_count: false,
        low_coverage: true,
        outlier_flag: false,
        outlier_details: null,
        images_used: 20,
        valid_coverage_pct: 30,
      },
    }

    renderWithProviders(
      <KPICards
        firstStats={firstStats}
        lastStats={lastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    expect(screen.getByText('Low coverage (30.0%)')).toBeInTheDocument()
  })

  it('shows outlier flag when detected', () => {
    const firstStats = { ...mockFirstStats }
    const lastStats = {
      ...mockLastStats,
      quality: {
        low_image_count: false,
        low_coverage: false,
        outlier_flag: true,
        outlier_details: 'Differs from neighbor average by 30.5%',
        images_used: 20,
        valid_coverage_pct: 90,
      },
    }

    renderWithProviders(
      <KPICards
        firstStats={firstStats}
        lastStats={lastStats}
        hasComparison={true}
        firstYear={2018}
        lastYear={2025}
      />
    )

    expect(screen.getByText('Outlier: Differs from neighbor average by 30.5%')).toBeInTheDocument()
  })
})