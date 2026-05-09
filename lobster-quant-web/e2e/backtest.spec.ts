import { test, expect } from '@playwright/test'

test.describe('Backtest Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/backtest')
  })

  test('should display backtest title', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Strategy Backtest')
  })

  test('should display backtest parameters card', async ({ page }) => {
    await expect(page.locator('text=Backtest Parameters')).toBeVisible()
  })

  test('should have symbol input field', async ({ page }) => {
    await expect(page.locator('input[placeholder*="SPY"]')).toBeVisible()
  })

  test('should have holding days slider', async ({ page }) => {
    await expect(page.locator('text=Holding Days')).toBeVisible()
  })

  test('should have minimum score slider', async ({ page }) => {
    await expect(page.locator('text=Minimum Score')).toBeVisible()
  })

  test('should have run backtest button', async ({ page }) => {
    await expect(page.locator('button:has-text("Run Backtest")')).toBeVisible()
  })

  test('should allow symbol input', async ({ page }) => {
    const input = page.locator('input[placeholder*="SPY"]')
    await input.fill('AAPL')
    await expect(input).toHaveValue('AAPL')
  })

  test('should allow holding days adjustment', async ({ page }) => {
    const slider = page.locator('[role="slider"]').first()
    await expect(slider).toBeVisible()
  })
})
