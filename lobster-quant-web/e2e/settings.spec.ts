import { test, expect } from '@playwright/test'

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
  })

  test('should display settings title', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Settings')
  })

  test('should display market configuration section', async ({ page }) => {
    await expect(page.locator('text=Market Configuration')).toBeVisible()
  })

  test('should display data configuration section', async ({ page }) => {
    await expect(page.locator('text=Data Configuration')).toBeVisible()
  })

  test('should display scoring weights section', async ({ page }) => {
    await expect(page.locator('text=Scoring Weights')).toBeVisible()
  })

  test('should have market toggles', async ({ page }) => {
    await expect(page.locator('text=US Stocks')).toBeVisible()
    await expect(page.locator('text=HK Stocks')).toBeVisible()
    await expect(page.locator('text=A-Shares')).toBeVisible()
  })

  test('should have data years slider', async ({ page }) => {
    await expect(page.locator('text=Data Years')).toBeVisible()
  })

  test('should have cache TTL slider', async ({ page }) => {
    await expect(page.locator('text=Cache TTL')).toBeVisible()
  })

  test('should have scoring weight sliders', async ({ page }) => {
    await expect(page.locator('text=Trend Weight')).toBeVisible()
    await expect(page.locator('text=Momentum Weight')).toBeVisible()
    await expect(page.locator('text=Volume Weight')).toBeVisible()
    await expect(page.locator('text=Pattern Weight')).toBeVisible()
  })

  test('should have save button', async ({ page }) => {
    await expect(page.locator('button:has-text("Save Settings")')).toBeVisible()
  })

  test('should have reset button', async ({ page }) => {
    await expect(page.locator('button:has-text("Reset")')).toBeVisible()
  })

  test('should show total scoring weight', async ({ page }) => {
    await expect(page.locator('text=Total:')).toBeVisible()
  })
})
