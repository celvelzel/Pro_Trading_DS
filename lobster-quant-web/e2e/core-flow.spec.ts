import { test, expect } from '@playwright/test'

/**
 * Core Flow E2E Tests
 *
 * Verifies the end-to-end user journey across all major pages:
 *   Dashboard → Scanner → Analysis → Backtest → Settings
 *
 * These tests exercise navigation, page rendering, and key interactive
 * elements to ensure the Next.js migration is fully functional.
 */

// ─── Helpers ────────────────────────────────────────────────────────

const PAGES = [
  { name: 'Dashboard', path: '/dashboard', heading: 'Dashboard' },
  { name: 'Scanner', path: '/scanner', heading: 'Stock Scanner' },
  { name: 'Analysis', path: '/analysis', heading: 'Stock Analysis' },
  { name: 'Backtest', path: '/backtest', heading: 'Strategy Backtest' },
  { name: 'Settings', path: '/settings', heading: 'Settings' },
] as const

// ─── Full Navigation Flow ───────────────────────────────────────────

test.describe('Core Flow — Full Navigation', () => {
  test('should visit every page in sequence and verify headings', async ({ page }) => {
    for (const pg of PAGES) {
      await page.goto(pg.path)
      await expect(page).toHaveURL(new RegExp(pg.path))
      await expect(page.locator('h1')).toHaveText(pg.heading)
    }
  })

  test('should navigate Dashboard → Scanner → Analysis → Backtest → Settings via sidebar', async ({
    page,
  }) => {
    // Start at Dashboard
    await page.goto('/dashboard')
    await expect(page.locator('h1')).toHaveText('Dashboard')

    // Dashboard → Scanner
    await page.click('text=Scanner')
    await expect(page).toHaveURL(/\/scanner/)
    await expect(page.locator('h1')).toHaveText('Stock Scanner')

    // Scanner → Analysis
    await page.click('text=Analysis')
    await expect(page).toHaveURL(/\/analysis/)
    await expect(page.locator('h1')).toHaveText('Stock Analysis')

    // Analysis → Backtest
    await page.click('text=Backtest')
    await expect(page).toHaveURL(/\/backtest/)
    await expect(page.locator('h1')).toHaveText('Strategy Backtest')

    // Backtest → Settings
    await page.click('text=Settings')
    await expect(page).toHaveURL(/\/settings/)
    await expect(page.locator('h1')).toHaveText('Settings')

    // Settings → Dashboard (full circle)
    await page.click('text=Dashboard')
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.locator('h1')).toHaveText('Dashboard')
  })
})

// ─── Dashboard ──────────────────────────────────────────────────────

test.describe('Core Flow — Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard')
  })

  test('should render the dashboard with key cards', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Dashboard')
    await expect(page.locator('text=Market Condition')).toBeVisible()
    await expect(page.locator('text=SPY Price')).toBeVisible()
    await expect(page.locator('text=ON/OFF Ratio')).toBeVisible()
  })

  test('should display the SPY price chart', async ({ page }) => {
    await expect(page.locator('text=SPY Price Chart')).toBeVisible()
  })

  test('should show quick access links to analysis', async ({ page }) => {
    await expect(page.locator('text=Quick Access')).toBeVisible()
    const stockLinks = page.locator('a[href^="/analysis/"]')
    await expect(stockLinks.first()).toBeVisible()
  })
})

// ─── Scanner ────────────────────────────────────────────────────────

test.describe('Core Flow — Scanner', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/scanner')
  })

  test('should render scanner with controls', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Stock Scanner')
    await expect(page.locator('text=Scan Parameters')).toBeVisible()
    await expect(page.locator('text=Market')).toBeVisible()
    await expect(page.locator('text=Minimum Score')).toBeVisible()
    await expect(page.locator('button:has-text("Scan")')).toBeVisible()
  })

  test('should open market dropdown and show all market options', async ({ page }) => {
    await page.click('[role="combobox"]')
    await expect(page.locator('text=US Stocks')).toBeVisible()
    await expect(page.locator('text=HK Stocks')).toBeVisible()
    await expect(page.locator('text=A-Shares')).toBeVisible()
  })
})

// ─── Analysis ───────────────────────────────────────────────────────

test.describe('Core Flow — Analysis', () => {
  test('should render analysis landing with input', async ({ page }) => {
    await page.goto('/analysis')
    await expect(page.locator('h1')).toHaveText('Stock Analysis')
    await expect(page.locator('input[placeholder*="AAPL"]')).toBeVisible()
    await expect(page.locator('button:has-text("Analyze")')).toBeVisible()
  })

  test('should navigate to stock detail on symbol submit', async ({ page }) => {
    await page.goto('/analysis')
    await page.fill('input[placeholder*="AAPL"]', 'MSFT')
    await page.click('button:has-text("Analyze")')
    await expect(page).toHaveURL(/\/analysis\/MSFT/)
  })

  test('should render stock detail page with tabs and metrics', async ({ page }) => {
    await page.goto('/analysis/AAPL')
    await expect(page.locator('h1')).toHaveText('AAPL')

    // Tabs
    await expect(page.locator('text=Overview')).toBeVisible()
    await expect(page.locator('text=Technical')).toBeVisible()
    await expect(page.locator('text=Options')).toBeVisible()
    await expect(page.locator('text=Signals')).toBeVisible()
    await expect(page.locator('text=Risk')).toBeVisible()

    // Key metrics
    await expect(page.locator('text=Volume')).toBeVisible()
    await expect(page.locator('text=RSI')).toBeVisible()
    await expect(page.locator('text=Signal Score')).toBeVisible()
  })

  test('should switch tabs on stock detail page', async ({ page }) => {
    await page.goto('/analysis/AAPL')
    await page.click('text=Technical')
    await expect(page.locator('text=RSI')).toBeVisible()
    await expect(page.locator('text=MACD')).toBeVisible()
  })
})

// ─── Backtest ───────────────────────────────────────────────────────

test.describe('Core Flow — Backtest', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/backtest')
  })

  test('should render backtest with parameters', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Strategy Backtest')
    await expect(page.locator('text=Backtest Parameters')).toBeVisible()
    await expect(page.locator('input[placeholder*="SPY"]')).toBeVisible()
    await expect(page.locator('text=Holding Days')).toBeVisible()
    await expect(page.locator('text=Minimum Score')).toBeVisible()
    await expect(page.locator('button:has-text("Run Backtest")')).toBeVisible()
  })

  test('should accept symbol input', async ({ page }) => {
    const input = page.locator('input[placeholder*="SPY"]')
    await input.fill('AAPL')
    await expect(input).toHaveValue('AAPL')
  })
})

// ─── Settings ───────────────────────────────────────────────────────

test.describe('Core Flow — Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
  })

  test('should render settings with all sections', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Settings')
    await expect(page.locator('text=Market Configuration')).toBeVisible()
    await expect(page.locator('text=Data Configuration')).toBeVisible()
    await expect(page.locator('text=Scoring Weights')).toBeVisible()
  })

  test('should display market toggles', async ({ page }) => {
    await expect(page.locator('text=US Stocks')).toBeVisible()
    await expect(page.locator('text=HK Stocks')).toBeVisible()
    await expect(page.locator('text=A-Shares')).toBeVisible()
  })

  test('should display scoring weight sliders', async ({ page }) => {
    await expect(page.locator('text=Trend Weight')).toBeVisible()
    await expect(page.locator('text=Momentum Weight')).toBeVisible()
    await expect(page.locator('text=Volume Weight')).toBeVisible()
    await expect(page.locator('text=Pattern Weight')).toBeVisible()
  })

  test('should have save and reset buttons', async ({ page }) => {
    await expect(page.locator('button:has-text("Save Settings")')).toBeVisible()
    await expect(page.locator('button:has-text("Reset")')).toBeVisible()
  })
})

// ─── Cross-cutting: Theme & Mobile ─────────────────────────────────

test.describe('Core Flow — Theme Toggle', () => {
  test('should toggle between light and dark themes', async ({ page }) => {
    await page.goto('/dashboard')
    const themeButton = page.locator('button:has-text("Toggle theme")')
    await expect(themeButton).toBeVisible()

    // Toggle to dark
    await themeButton.click()
    await expect(page.locator('html')).toHaveClass(/dark/)

    // Toggle back to light
    await themeButton.click()
    await expect(page.locator('html')).not.toHaveClass(/dark/)
  })
})

test.describe('Core Flow — Mobile Navigation', () => {
  test('should show mobile bottom nav and navigate', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard')

    // Mobile nav should be visible
    await expect(page.locator('nav.md\\:hidden')).toBeVisible()

    // Navigate via mobile nav
    await page.click('nav.md\\:hidden >> text=Scanner')
    await expect(page).toHaveURL(/\/scanner/)
  })
})
