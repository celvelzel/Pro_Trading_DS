import { existsSync, readFileSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'
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
      const panel = page.getByRole('article', { name: new RegExp(`run ${id}$`) })
      await expect(panel).toHaveCount(1)
      await expect(panel).toBeVisible()
      await expect(panel.getByRole('status').first()).toContainText('completed', { timeout: 60000 })
      await expect(panel.getByRole('status').first()).toContainText(/cursor [1-9]/)
      await expect(panel.getByText(/mas.completed/)).toBeVisible({ timeout: 60000 })
    }
    if (workflow === 'combined') {
      await expect(page.getByText(/cross_mas.linked/).first()).toBeVisible()
      await expect(page.getByText(/cross_mas.admitted/).first()).toBeVisible()
      await expect(page.getByText(/relation_id:/).first()).toBeVisible()
    }
    await expect(page.getByText(workflow === 'portfolio' ? 'Portfolio 合成来源与计算记录' : '来源与证据详情').first()).toBeVisible()
  })
}
for (const workflow of ['portfolio', 'combined'] as const) {
test(`Portfolio ${workflow} entry uses synthetic request and preserves holdings/cash bytes`, async ({ page }) => {
  test.setTimeout(90000)
  const dataDirectory = process.env.FINANCIAL_E2E_PORTFOLIO_DATA_DIR || resolve(process.cwd(), '../backend/data/portfolio')
  expect(existsSync(dataDirectory), 'API portfolio storage directory must exist').toBe(true)
  expect(statSync(dataDirectory).isDirectory(), 'API portfolio storage path must be a directory').toBe(true)
  const digest = () => ['positions.json', 'cash.json'].map(name => {
    const path = resolve(dataDirectory, name)
    return existsSync(path) ? { exists: true, sha256: createHash('sha256').update(readFileSync(path)).digest('hex') } : { exists: false, sha256: null }
  })
  const beforeServer = digest()
  const writes: string[] = []
  page.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/portfolio') && !['GET', 'HEAD', 'OPTIONS'].includes(request.method())) writes.push(request.method()) })
  await page.goto('/portfolio')
  const before = await page.evaluate(() => JSON.stringify({ ...localStorage }))
  await expect(page.getByRole('link', { name: 'Portfolio 合成只读演示' })).toHaveAttribute('href', '/copilot?workflow=portfolio')
  await page.getByRole('link', { name: workflow === 'portfolio' ? 'Portfolio 合成只读演示' : 'Combined 合成只读演示' }).click()
  await page.getByRole('combobox', { name: '金融执行模式' }).selectOption('auto')
  const requestPromise = page.waitForRequest(request => request.url().includes(`/api/financial/${workflow === 'portfolio' ? 'portfolio-reviews' : 'combined-reviews'}`) && request.method() === 'POST')
  await page.getByRole('button', { name: `开始 ${workflow} 合成演示` }).click()
  const body = (await requestPromise).postDataJSON()
  expect(body.portfolio.portfolio_snapshot_id).toBe('synthetic-mu-soxx-v1')
  expect(Object.keys(body.portfolio).sort()).toEqual(['as_of', 'portfolio_snapshot_id', 'user_constraints'])
  expect(JSON.stringify(body)).not.toMatch(/holdings|cash_balance|positions/)
  if (workflow === 'portfolio') expect(body).not.toHaveProperty('market')
  await expect(page.getByRole('article')).toHaveCount(workflow === 'combined' ? 2 : 1)
  for (const panel of await page.getByRole('article').all()) {
    await expect(panel.getByRole('status').first()).toContainText('completed', { timeout: 60000 })
    await expect(panel.getByText(/mas.completed/)).toBeVisible({ timeout: 60000 })
  }
  expect(JSON.stringify(digest()) === JSON.stringify(beforeServer), 'portfolio storage bytes and existence stay unchanged').toBe(true)
  expect(writes).toEqual([])
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage }))).toBe(before)
})
}

test('Analysis link scopes the Market synthetic demo to the selected symbol', async ({ page }) => {
  await page.goto('/analysis/MU')
  const link = page.getByRole('link', { name: '此标的 Market 合成只读演示' })
  await expect(link).toBeVisible({ timeout: 30000 })
  await expect(link).toHaveAttribute('href', /workflow=market.*symbol=MU/)
  await link.click()
  await expect(page.getByRole('textbox', { name: 'Market symbol' })).toHaveValue('MU')
})

test('General still uses its legacy create endpoint and independent mode', async ({ page }) => {
  await page.goto('/copilot')
  await expect(page.getByRole('combobox', { name: 'Workflow' })).toHaveValue('general')
  await page.getByLabel('研究目标').fill('Synthetic compatibility smoke: inspect available tools')
  const received = page.waitForResponse(response => response.url().endsWith('/api/agent/runs') && response.request().method() === 'POST')
  await page.getByRole('button', { name: '开始规划' }).click()
  const response = await received
  expect(response.ok()).toBe(true)
  expect(response.request().postDataJSON()).toMatchObject({ goal: 'Synthetic compatibility smoke: inspect available tools', mode: 'review' })
})
