import { test, expect } from '@playwright/test'

test('natural-language constraints reach the actual API and exclude an all-cash proposal', async ({ page }) => {
  await page.goto('/copilot?workflow=portfolio')
  await page.getByRole('combobox', { name: '金融执行模式' }).selectOption('auto')
  await page.getByLabel('用自然语言描述').fill('MU不超过25%，现金20%–30%，股票总仓位最多80%')
  await expect(page.getByRole('checkbox', { name: '确认组合约束' })).toBeDisabled()
  const parse = page.waitForResponse(r => r.url().includes('/constraints/parse'))
  await page.getByRole('button', { name: '解析为约束草稿' }).click()
  expect((await parse).status()).toBe(200)
  await page.getByRole('button', { name: '将草稿填入表单' }).click()
  await expect(page.getByLabel('现金最高比例 (%)')).toHaveValue('30')
  await page.screenshot({ path: '../logs/financial-mas/check-20261011/constraints-form.png', fullPage: true })
  await page.getByRole('checkbox', { name: '确认组合约束' }).check()
  const creation = page.waitForResponse(r => r.url().endsWith('/portfolio-reviews') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '开始 portfolio 合成演示' }).click()
  const response = await creation
  expect(response.status()).toBe(202)
  const body = response.request().postDataJSON()
  expect(body.portfolio.user_constraints.max_weight_by_symbol.CASH).toBe(.3)
  expect(body.portfolio.user_constraints.min_cash_weight).toBe(.2)
  await expect(page.getByRole('article').getByRole('status').first()).toContainText('completed', { timeout: 60000 })
  const rid = (await response.json()).portfolio_run_id
  const result = await page.request.get('http://localhost:8001/api/financial/runs/' + rid)
  const artifact = (await result.json()).artifact
  expect(artifact.status).toBe('feasible')
  expect(artifact.proposed_weights.CASH).toBeLessThanOrEqual(.3)
})

test('vague natural language stays unresolved and cannot start a run', async ({ page }) => {
  await page.goto('/copilot?workflow=portfolio')
  await page.getByLabel('用自然语言描述').fill('稳健一点，股票至少50%')
  await page.getByRole('button', { name: '解析为约束草稿' }).click()
  await expect(page.getByText(/待澄清：.*稳健一点/)).toBeVisible()
  await expect(page.getByRole('button', { name: '将草稿填入表单' })).toBeDisabled()
  await expect(page.getByRole('button', { name: '开始 portfolio 合成演示' })).toBeDisabled()
  await page.getByRole('button', { name: '清除描述，手动填写' }).click()
  await page.getByRole('checkbox', { name: '确认组合约束' }).check()
  await expect(page.getByRole('button', { name: '开始 portfolio 合成演示' })).toBeEnabled()
})
