import { test, expect } from '@playwright/test'

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard')
  })

  test('should display dashboard title', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('Dashboard')
  })

  test('should display market condition card', async ({ page }) => {
    await expect(page.locator('text=Market Condition')).toBeVisible()
  })

  test('should display SPY price card', async ({ page }) => {
    await expect(page.locator('text=SPY Price')).toBeVisible()
  })

  test('should display ON/OFF ratio card', async ({ page }) => {
    await expect(page.locator('text=ON/OFF Ratio')).toBeVisible()
  })

  test('should display price chart', async ({ page }) => {
    await expect(page.locator('text=SPY Price Chart')).toBeVisible()
  })

  test('should display quick access section', async ({ page }) => {
    await expect(page.locator('text=Quick Access')).toBeVisible()
  })

  test('should have working navigation links', async ({ page }) => {
    // Check that stock links are present
    const stockLinks = page.locator('a[href^="/analysis/"]')
    await expect(stockLinks.first()).toBeVisible()
  })
})
