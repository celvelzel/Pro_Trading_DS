import { test, expect } from '@playwright/test'

test.describe('Analysis Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/analysis')
  })

  test('should display analysis title', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Stock Analysis')
  })

  test('should have symbol input field', async ({ page }) => {
    await expect(page.locator('input[placeholder*="AAPL"]')).toBeVisible()
  })

  test('should have analyze button', async ({ page }) => {
    await expect(page.locator('button:has-text("Analyze")')).toBeVisible()
  })

  test('should navigate to stock analysis on submit', async ({ page }) => {
    // Fill in the symbol
    await page.fill('input[placeholder*="AAPL"]', 'AAPL')
    
    // Click analyze button
    await page.click('button:has-text("Analyze")')
    
    // Should navigate to the stock analysis page
    await expect(page).toHaveURL(/\/analysis\/AAPL/)
  })
})

test.describe('Analysis Detail Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/analysis/AAPL')
  })

  test('should display stock symbol', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('AAPL')
  })

  test('should display price information', async ({ page }) => {
    // Should show price
    await expect(page.locator('text=$')).toBeVisible()
  })

  test('should have analysis tabs', async ({ page }) => {
    await expect(page.locator('text=Overview')).toBeVisible()
    await expect(page.locator('text=Technical')).toBeVisible()
    await expect(page.locator('text=Options')).toBeVisible()
    await expect(page.locator('text=Signals')).toBeVisible()
    await expect(page.locator('text=Risk')).toBeVisible()
  })

  test('should switch between tabs', async ({ page }) => {
    // Click Technical tab
    await page.click('text=Technical')
    
    // Should show technical indicators
    await expect(page.locator('text=RSI')).toBeVisible()
    await expect(page.locator('text=MACD')).toBeVisible()
  })

  test('should display key metrics', async ({ page }) => {
    await expect(page.locator('text=Volume')).toBeVisible()
    await expect(page.locator('text=RSI')).toBeVisible()
    await expect(page.locator('text=ATR %')).toBeVisible()
    await expect(page.locator('text=Signal Score')).toBeVisible()
  })
})
