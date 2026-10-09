import { test, expect } from '@playwright/test'
// Actual typed API only: no route mocks. Run with the synthetic API service available.
for (const workflow of ['market', 'portfolio', 'combined']) {
  test(`${workflow} typed synthetic end-to-end`, async ({ page }) => {
    test.setTimeout(90000)
    await page.goto(`/copilot?workflow=${workflow}&symbol=MU`)
    await page.getByRole('combobox', { name: '金融执行模式' }).selectOption('auto')
    const createdResponse = page.waitForResponse(response => response.url().includes('/api/financial/') && response.request().method() === 'POST')
    await page.getByRole('button', { name: `开始 ${workflow} 合成演示` }).click()
    const response = await createdResponse
    expect(response.status()).toBe(202)
    const created = await response.json()
    expect(created.runs).toHaveLength(workflow === 'combined' ? 2 : 1)
    const ids = created.runs.map((run: { run_id: string }) => run.run_id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const id of ids) {
      await expect(page.getByText(id, { exact: true })).toBeVisible()
      const panel = page.getByRole('article').filter({ has: page.getByText(id, { exact: true }) })
      await expect(panel.getByRole('status').first()).toContainText('completed', { timeout: 60000 })
      await expect(panel.getByRole('status').first()).toContainText(/cursor [1-9]/)
    }
    await expect(page.getByText('来源与证据详情').first()).toBeVisible()
  })
}
test('Portfolio links use synthetic request and leave local holdings/cash byte-identical', async ({ page }) => {
  test.setTimeout(90000)
  await page.goto('/portfolio')
  const before = await page.evaluate(() => JSON.stringify({ ...localStorage }))
  await expect(page.getByRole('link', { name: 'Portfolio 合成只读演示' })).toHaveAttribute('href', '/copilot?workflow=portfolio')
  await page.getByRole('link', { name: 'Combined 合成只读演示' }).click()
  await page.getByRole('combobox', { name: '金融执行模式' }).selectOption('auto')
  const requestPromise = page.waitForRequest(request => request.url().includes('/api/financial/combined-reviews') && request.method() === 'POST')
  await page.getByRole('button', { name: '开始 combined 合成演示' }).click()
  const body = (await requestPromise).postDataJSON()
  expect(body.portfolio.portfolio_snapshot_id).toBe('synthetic-mu-soxx-v1')
  expect(body.portfolio).not.toHaveProperty('positions'); expect(body.portfolio).not.toHaveProperty('cash')
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage }))).toBe(before)
})
test('Analysis link scopes the Market synthetic demo to the selected symbol', async ({ page }) => {
  await page.goto('/analysis/MU')
  const link = page.getByRole('link', { name: '此标的 Market 合成只读演示' })
  await expect(link).toBeVisible({ timeout: 30000 })
  await expect(link).toHaveAttribute('href', /workflow=market.*symbol=MU/)
  await link.click()
  await expect(page.getByRole('textbox', { name: 'Market symbol' })).toHaveValue('MU')
})
