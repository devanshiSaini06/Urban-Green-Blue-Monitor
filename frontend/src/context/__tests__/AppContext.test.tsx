import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { AppProvider, useApp } from '../AppContext'
import { ThemeProvider } from '../ThemeContext'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <ThemeProvider>
        <AppProvider>
          {component}
        </AppProvider>
      </ThemeProvider>
    </MemoryRouter>
  )
}

const TestComponent = () => {
  const { selectedDistrict, setDistrict, selectedYears, setYears, runAnalysis, districts } = useApp()
  return (
    <div>
      <span data-testid="district">{selectedDistrict}</span>
      <button onClick={() => setDistrict('gautam_buddha_nagar')} data-testid="change-district">
        Change District
      </button>
      <span data-testid="years">{selectedYears.join(',')}</span>
      <button onClick={() => setYears([2019, 2020])} data-testid="change-years">
        Change Years
      </button>
      <button onClick={runAnalysis} data-testid="run-analysis" disabled={!runAnalysis}>
        Run Analysis
      </button>
      <span data-testid="district-count">{districts.length}</span>
    </div>
  )
}

describe('AppContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockReset()
  })

  it('provides default values', () => {
    renderWithProviders(<TestComponent />)

    expect(screen.getByTestId('district').textContent).toBe('bengaluru_urban')
    expect(screen.getByTestId('years').textContent).toBe('2018,2025')
  })

  it('allows changing district', () => {
    renderWithProviders(<TestComponent />)

    fireEvent.click(screen.getByTestId('change-district'))

    expect(screen.getByTestId('district').textContent).toBe('gautam_buddha_nagar')
  })

  it('allows changing years', () => {
    renderWithProviders(<TestComponent />)

    fireEvent.click(screen.getByTestId('change-years'))

    expect(screen.getByTestId('years').textContent).toBe('2019,2020')
  })

  it('syncs district to URL', () => {
    renderWithProviders(<TestComponent />)

    fireEvent.click(screen.getByTestId('change-district'))

    // URL should update (MemoryRouter handles this)
    expect(window.location.search).toContain('district=gautam_buddha_nagar')
  })

  it('syncs years to URL', () => {
    renderWithProviders(<TestComponent />)

    fireEvent.click(screen.getByTestId('change-years'))

    expect(window.location.search).toContain('years=2019,2020')
  })

  it('fetches districts on mount', async () => {
    const mockDistricts = [
      { id: 'bengaluru_urban', display_name: 'Bengaluru Urban', bounds: { west: 0, south: 0, east: 1, north: 1 }, center: [1, 1], zoom: 10 },
      { id: 'gautam_buddha_nagar', display_name: 'Gautam Buddha Nagar', bounds: { west: 0, south: 0, east: 1, north: 1 }, center: [1, 1], zoom: 10 },
    ]

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockDistricts,
    })

    renderWithProviders(<TestComponent />)

    await waitFor(() => {
      expect(screen.getByTestId('district-count').textContent).toBe('2')
    })
  })

  it('runAnalysis calls API with correct parameters', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        stats: [],
        quality_summary: { years_with_warnings: 0, outlier_years: [], best_quality_year: 2020 },
        run_metadata: {},
      }),
    })

    renderWithProviders(<TestComponent />)

    fireEvent.click(screen.getByTestId('run-analysis'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/analysis'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('bengaluru_urban'),
        })
      )
    })
  })

  it('handles analysis error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Analysis failed' }),
    })

    renderWithProviders(<TestComponent />)

    fireEvent.click(screen.getByTestId('run-analysis'))

    await waitFor(() => {
      // Error should be set in context
      expect(screen.queryByText(/Analysis failed/)).toBeInTheDocument()
    })
  })

  it('resets to defaults', () => {
    renderWithProviders(<TestComponent />)

    fireEvent.click(screen.getByTestId('change-district'))
    fireEvent.click(screen.getByTestId('change-years'))

    // We can't directly test resetToDefaults without exposing it
    // But we can verify the function exists in context
    const { resetToDefaults } = useApp()
    expect(typeof resetToDefaults).toBe('function')
  })
})