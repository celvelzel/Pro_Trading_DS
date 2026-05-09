import { test, expect } from '@playwright/test'

test.describe('Scanner Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/scanner')
  })

  test('should display scanner title', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Stock Scanner')
  })

  test('should display scan parameters card', async ({ page }) => {
    await expect(page.locator('text=Scan Parameters')).toBeVisible()
  })

  test('should have market selection dropdown', async ({ page }) => {
    await expect(page.locator('text=Market')).toBeVisible()
  })

  test('should have minimum score slider', async ({ page }) => {
    await expect(page.locator('text=Minimum Score')).toBeVisible()
  })

  test('should have scan button', async ({ page }) => {
    await expect(page.locator('button:has-text("Scan")')).toBeVisible()
  })

  test('should allow market selection', async ({ page }) => {
    // Click the market selector
    await page.click('[role="combobox"]')
    
    // Check that options are visible
    await expect(page.locator('text=US Stocks')).toBeVisible()
    await expect(page.locator('text=HK Stocks')).toBeVisible()
    await expect(page.locator('text=A-Shares')).toBeVisible()
  })

  test('should allow score adjustment', async ({ page }) => {
    // The slider should be present
    const slider = page.locator('[role="slider"]')
    await expect(slider).toBeVisible()
  })
})
