import { test, expect } from '@playwright/test'

test.describe('Simulation Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/simulation')
  })

  test('should display simulation title', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Daily Simulation')
  })

  test('should display strategy selector', async ({ page }) => {
    await expect(page.locator('text=Strategy')).toBeVisible()
  })

  test('should display market selector', async ({ page }) => {
    await expect(page.locator('text=Market')).toBeVisible()
  })

  test('should have run simulation button', async ({ page }) => {
    await expect(page.locator('button:has-text("Run Today")')).toBeVisible()
  })

  test('should have run all button', async ({ page }) => {
    await expect(page.locator('button:has-text("Run All")')).toBeVisible()
  })

  test('should display simulation tabs', async ({ page }) => {
    await expect(page.locator('text=Trades')).toBeVisible()
    await expect(page.locator('text=Journal')).toBeVisible()
    await expect(page.locator('text=Performance')).toBeVisible()
  })

  test('should switch between tabs', async ({ page }) => {
    // Click Journal tab
    await page.click('text=Journal')
    // The journal tab content should be active
    await expect(page.locator('[role="tabpanel"]').last()).toBeVisible()

    // Click Performance tab
    await page.click('text=Performance')
    await expect(page.locator('[role="tabpanel"]').last()).toBeVisible()
  })

  test('should have export button', async ({ page }) => {
    await expect(page.locator('button:has-text("Export")')).toBeVisible()
  })
})
