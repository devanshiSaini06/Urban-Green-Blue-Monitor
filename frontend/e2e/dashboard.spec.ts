import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Wait for app to load
    await page.waitForSelector('text=Urban Green & Blue Monitor', { timeout: 10000 })
  })

  test('loads dashboard with default district', async ({ page }) => {
    await expect(page.locator('text=Bengaluru Urban')).toBeVisible()
    await expect(page.locator('text=Run Analysis')).toBeVisible()
  })

  test('shows year selector with all study years', async ({ page }) => {
    const years = ['2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']
    for (const year of years) {
      await expect(page.locator(`button:has-text("${year}")`)).toBeVisible()
    }
  })

  test('can select multiple years', async ({ page }) => {
    await page.click('button:has-text("2018")')
    await page.click('button:has-text("2025")')

    await expect(page.locator('button:has-text("2018")')).toHaveClass(/bg-primary-600/)
    await expect(page.locator('button:has-text("2025")')).toHaveClass(/bg-primary-600/)
  })

  test('shows Clear button after selecting years', async ({ page }) => {
    await page.click('button:has-text("2018")')
    await expect(page.locator('button:has-text("Clear")')).toBeVisible()
  })

  test('can clear year selection', async ({ page }) => {
    await page.click('button:has-text("2018")')
    await page.click('button:has-text("Clear")')

    await expect(page.locator('button:has-text("2018")')).not.toHaveClass(/bg-primary-600/)
  })

  test('can switch classifier', async ({ page }) => {
    await page.click('button:has-text("Dynamic World")')
    await expect(page.locator('button:has-text("Dynamic World")')).toHaveClass(/bg-white/)
  })

  test('can change season', async ({ page }) => {
    await page.selectOption('select', 'jan-mar')
    await expect(page.locator('select')).toHaveValue('jan-mar')
  })

  test('shows threshold sliders for spectral classifier', async ({ page }) => {
    // Default is spectral
    await expect(page.locator('text=Classification Thresholds')).toBeVisible()
  })

  test('hides threshold sliders for Dynamic World', async ({ page }) => {
    await page.click('button:has-text("Dynamic World")')
    await expect(page.locator('text=Classification Thresholds')).not.toBeVisible()
  })

  test('can toggle threshold panel', async ({ page }) => {
    await page.click('button:has-text("Classification Thresholds")')
    await expect(page.locator('text=MNDWI > Water')).toBeVisible()

    await page.click('button:has-text("Classification Thresholds")')
    await expect(page.locator('text=MNDWI > Water')).not.toBeVisible()
  })
})

test.describe('Map View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/map')
    await page.waitForSelector('text=Urban Green & Blue Monitor', { timeout: 10000 })
  })

  test('loads map view', async ({ page }) => {
    await expect(page.locator('text=Map')).toBeVisible()
  })

  test('shows layer controls', async ({ page }) => {
    await expect(page.locator('text=Layers')).toBeVisible()
    await expect(page.locator('text=True Color')).toBeVisible()
    await expect(page.locator('text=NDVI')).toBeVisible()
    await expect(page.locator('text=Land Cover')).toBeVisible()
  })

  test('shows year slider', async ({ page }) => {
    await expect(page.locator('text=Year:')).toBeVisible()
    await expect(page.locator('input[type="range"]')).toBeVisible()
  })

  test('shows play/pause button', async ({ page }) => {
    await expect(page.locator('button[aria-label="Play animation"]')).toBeVisible()
  })

  test('shows opacity slider', async ({ page }) => {
    await expect(page.locator('text=Opacity')).toBeVisible()
    await expect(page.locator('input[type="range"][min="0"][max="1"]')).toBeVisible()
  })

  test('shows boundary toggle', async ({ page }) => {
    await expect(page.locator('text=Show boundary')).toBeVisible()
  })
})

test.describe('Analysis Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/analysis')
    await page.waitForSelector('text=Urban Green & Blue Monitor', { timeout: 10000 })
  })

  test('shows analysis tabs', async ({ page }) => {
    await expect(page.locator('text=Trends')).toBeVisible()
    await expect(page.locator('text=Transitions')).toBeVisible()
    await expect(page.locator('text=Landscape Metrics')).toBeVisible()
    await expect(page.locator('text=Urban Growth')).toBeVisible()
    await expect(page.locator('text=Environmental')).toBeVisible()
    await expect(page.locator('text=Lakes')).toBeVisible()
    await expect(page.locator('text=Hotspots')).toBeVisible()
  })

  test('shows placeholder when no analysis run', async ({ page }) => {
    await expect(page.locator('text=Run an analysis first')).toBeVisible()
  })
})

test.describe('Report Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/report')
    await page.waitForSelector('text=Urban Green & Blue Monitor', { timeout: 10000 })
  })

  test('shows report page', async ({ page }) => {
    await expect(page.locator('text=Generate Report')).toBeVisible()
  })

  test('shows message when no analysis', async ({ page }) => {
    await expect(page.locator('text=No analysis data available')).toBeVisible()
  })
})

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForSelector('text=Urban Green & Blue Monitor', { timeout: 10000 })
  })

  test('shows theme selector', async ({ page }) => {
    await expect(page.locator('text=Appearance')).toBeVisible()
    await expect(page.locator('text=Light')).toBeVisible()
    await expect(page.locator('text=Dark')).toBeVisible()
    await expect(page.locator('text=System')).toBeVisible()
  })

  test('shows cache management', async ({ page }) => {
    await expect(page.locator('text=Cache Management')).toBeVisible()
    await expect(page.locator('text=Clear Cache')).toBeVisible()
  })

  test('shows important notes', async ({ page }) => {
    await expect(page.locator('text=Important Notes')).toBeVisible()
    await expect(page.locator('text=2018 data may have lower image count')).toBeVisible()
    await expect(page.locator('text=Built-up class from spectral rules includes bare soil')).toBeVisible()
  })
})

test.describe('URL State Persistence', () => {
  test('preserves state in URL', async ({ page }) => {
    await page.goto('/')

    // Select years
    await page.click('button:has-text("2019")')
    await page.click('button:has-text("2020")')

    // Check URL
    await expect(page).toHaveURL(/years=2019,2020/)

    // Reload page
    await page.reload()
    await page.waitForSelector('text=Urban Green & Blue Monitor')

    // State should be restored
    await expect(page.locator('button:has-text("2019")')).toHaveClass(/bg-primary-600/)
    await expect(page.locator('button:has-text("2020")')).toHaveClass(/bg-primary-600/)
  })

  test('preserves district in URL', async ({ page }) => {
    await page.goto('/?district=gautam_buddha_nagar')
    await page.waitForSelector('text=Urban Green & Blue Monitor')

    await expect(page.locator('text=Gautam Buddha Nagar')).toBeVisible()
  })

  test('preserves classifier in URL', async ({ page }) => {
    await page.goto('/?classifier=dynamic_world')
    await page.waitForSelector('text=Urban Green & Blue Monitor')

    await expect(page.locator('button:has-text("Dynamic World")')).toHaveClass(/bg-white/)
  })
})

test.describe('Dark Mode', () => {
  test('toggles dark mode', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('text=Urban Green & Blue Monitor')

    // Click theme toggle
    await page.click('button[aria-label="Switch to dark mode"]')

    // Check dark class on html
    await expect(page.locator('html')).toHaveClass(/dark/)

    // Toggle back
    await page.click('button[aria-label="Switch to light mode"]')
    await expect(page.locator('html')).not.toHaveClass(/dark/)
  })
})

test.describe('Accessibility', () => {
  test('has proper ARIA labels', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('text=Urban Green & Blue Monitor')

    // Year buttons should have aria-pressed
    const buttons = page.locator('button[aria-pressed]')
    await expect(buttons.first()).toHaveAttribute('aria-pressed', 'false')
  })

  test('focus visible styles', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('text=Urban Green & Blue Monitor')

    // Tab to first focusable element
    await page.keyboard.press('Tab')
    const focused = page.locator(':focus')
    await expect(focused).toBeVisible()
  })
})