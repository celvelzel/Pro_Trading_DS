import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('should navigate between pages using sidebar', async ({ page }) => {
    await page.goto('/dashboard')
    
    // Click Scanner link
    await page.click('text=Scanner')
    await expect(page).toHaveURL(/\/scanner/)
    await expect(page.locator('h1')).toHaveText('Stock Scanner')
    
    // Click Analysis link
    await page.click('text=Analysis')
    await expect(page).toHaveURL(/\/analysis/)
    await expect(page.locator('h1')).toHaveText('Stock Analysis')
    
    // Click Backtest link
    await page.click('text=Backtest')
    await expect(page).toHaveURL(/\/backtest/)
    await expect(page.locator('h1')).toHaveText('Strategy Backtest')
    
    // Click Settings link
    await page.click('text=Settings')
    await expect(page).toHaveURL(/\/settings/)
    await expect(page.locator('h1')).toHaveText('Settings')
    
    // Click Dashboard link
    await page.click('text=Dashboard')
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.locator('h1')).toHaveText('Dashboard')
  })

  test('should navigate using mobile bottom nav', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard')
    
    // Mobile nav should be visible
    await expect(page.locator('nav.md\\:hidden')).toBeVisible()
    
    // Click Scanner in mobile nav
    await page.click('nav.md\\:hidden >> text=Scanner')
    await expect(page).toHaveURL(/\/scanner/)
  })

  test('should navigate to stock analysis from search', async ({ page }) => {
    await page.goto('/dashboard')
    
    // Fill in search
    await page.fill('input[placeholder*="AAPL"]', 'MSFT')
    
    // Submit search
    await page.press('input[placeholder*="AAPL"]', 'Enter')
    
    // Should navigate to analysis page
    await expect(page).toHaveURL(/\/analysis\/MSFT/)
  })

  test('should have working theme toggle', async ({ page }) => {
    await page.goto('/dashboard')
    
    // Theme toggle should be visible
    const themeButton = page.locator('button:has-text("Toggle theme")')
    await expect(themeButton).toBeVisible()
    
    // Click to toggle theme
    await themeButton.click()
    
    // Should have dark class on html
    await expect(page.locator('html')).toHaveClass(/dark/)
  })
})
