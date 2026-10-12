import { test, expect } from '@playwright/test'

for (const theme of ['light', 'dark']) {
  for (const width of [390, 1440]) {
    test(`settings navigation and theme render at ${width}px in ${theme}`, async ({ page }) => {
      const errors: string[] = []
      page.on('pageerror', error => errors.push(error.message))
      await page.addInitScript(value => localStorage.setItem('theme', value), theme)
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/settings/scoring')
      await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible()
      await expect(page.locator('html')).toHaveClass(new RegExp(theme))
      for (const [label, route] of [
        ['Scoring', 'scoring'], ['Data & Markets', 'data'], ['Backtest', 'backtest'],
        ['OFF Filter', 'off-filter'], ['Import / Export', 'import-export'],
      ]) {
        await page.getByRole('navigation', { name: 'Settings sections' }).getByRole('link', { name: label, exact: true }).click()
        await expect(page).toHaveURL(new RegExp(`/settings/${route}$`))
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      }
      await page.getByRole('button', { name: 'Toggle color theme' }).click()
      await expect(page.locator('html')).toHaveClass(new RegExp(theme === 'dark' ? 'light' : 'dark'))
      if (width === 390) {
        await page.getByRole('button', { name: 'Open navigation menu' }).click()
        await page.getByRole('dialog').getByRole('link', { name: 'Knowledge', exact: true }).click()
        await expect(page).toHaveURL(/\/knowledge$/)
        await expect(page.getByRole('heading', { name: 'Knowledge', exact: true })).toBeVisible()
      }
      expect(errors).toEqual([])
    })
  }
}

for (const theme of ['light', 'dark']) {
  test(`loaded market chart follows ${theme} theme without rendering errors`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.addInitScript(value => localStorage.setItem('theme', value), theme)
    await page.setViewportSize({ width: 390, height: 844 })
    const candles = Array.from({ length: 45 }, (_, i) => ({ time: 1700000000 + i * 86400, open: 100 + i, high: 104 + i, low: 98 + i, close: 102 + i, volume: 1000000 }))
    await page.route('**/api/**', async route => {
      const path = new URL(route.request().url()).pathname
      let value: unknown
      if (/\/stocks\/[^/]+$/.test(path)) value = { symbol: path.split('/').at(-1), name: 'Visual QA fixture', price: 146, change: 2, changePercent: 1.39, volume: 1000000, candles }
      else if (path.endsWith('/risk')) value = { status: 'on', statusText: 'ON', reasons: ['Fixture'], onPercent: 80, offPercent: 20 }
      else if (path.endsWith('/strategies') || path.endsWith('/history')) value = []
      else if (path.endsWith('/signals')) value = { type: 'bullish', score: 75, probability: 70, reasons: ['Fixture'] }
      else { await route.fulfill({ status: 503, json: { detail: 'Not included in visual QA fixture' } }); return }
      await route.fulfill({ json: value })
    })
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible()
    await expect(page.locator('canvas').first()).toBeVisible()
    await expect(page.getByText('Something went wrong', { exact: true })).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.getByRole('button', { name: 'Toggle color theme' }).click()
    await expect(page.locator('html')).toHaveClass(new RegExp(theme === 'dark' ? 'light' : 'dark'))
    await expect(page.locator('canvas').first()).toBeVisible()
    expect(errors).toEqual([])
  })
}
