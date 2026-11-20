import { render, screen, fireEvent } from '@testing-library/react'
import { YearSelector } from '../YearSelector'
import { AppProvider } from '../../context/AppContext'
import { ThemeProvider } from '../../context/ThemeContext'
import { MemoryRouter } from 'react-router-dom'

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

describe('YearSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all study years as buttons', () => {
    renderWithProviders(<YearSelector />)

    const years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    years.forEach(year => {
      expect(screen.getByRole('button', { name: String(year) })).toBeInTheDocument()
    })
  })

  it('shows selected years with primary styling', () => {
    renderWithProviders(<YearSelector />)

    // Initially no years selected
    const buttons = screen.getAllByRole('button', { name: /2018|2019|2020|2021|2022|2023|2024|2025/ })
    buttons.forEach(btn => {
      expect(btn).not.toHaveClass('bg-primary-600')
    })
  })

  it('toggles year selection on click', () => {
    renderWithProviders(<YearSelector />)

    const button2018 = screen.getByRole('button', { name: '2018' })
    fireEvent.click(button2018)

    expect(button2018).toHaveClass('bg-primary-600')
    expect(button2018).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows Clear button when years are selected', () => {
    renderWithProviders(<YearSelector />)

    expect(screen.queryByText('Clear')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '2018' }))
    expect(screen.getByText('Clear')).toBeInTheDocument()
  })

  it('clears all selections on Clear click', () => {
    renderWithProviders(<YearSelector />)

    fireEvent.click(screen.getByRole('button', { name: '2018' }))
    fireEvent.click(screen.getByRole('button', { name: '2019' }))

    fireEvent.click(screen.getByText('Clear'))

    const buttons = screen.getAllByRole('button', { name: /2018|2019|2020|2021|2022|2023|2024|2025/ })
    buttons.forEach(btn => {
      expect(btn).not.toHaveClass('bg-primary-600')
    })
  })

  it('does not allow years outside study period', () => {
    renderWithProviders(<YearSelector />)

    // Should only have 2018-2025
    const buttons = screen.getAllByRole('button', { name: /\d{4}/ })
    expect(buttons).toHaveLength(8)
  })
})