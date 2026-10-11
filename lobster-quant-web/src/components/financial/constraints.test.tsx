import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi, it, expect, beforeEach } from 'vitest'
import { FinancialWorkflow } from './FinancialWorkflow'
import { financialApi } from '@/lib/financial-api'
import { agentApi } from '@/lib/agent-api'
vi.mock('@/hooks/useFinancialEvents', () => ({ useFinancialEvents: () => ({ events: [], cursor: 0, connection: 'connecting' }) }))

beforeEach(() => { vi.restoreAllMocks() })

it('requires confirmation and invalidates it on manual edits', () => {
  render(<FinancialWorkflow workflow="portfolio" mode="auto" />)
  const start = screen.getByRole('button', { name: '开始 portfolio 合成演示' })
  expect(start).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox', { name: '确认组合约束' }))
  expect(start).toBeEnabled()
  fireEvent.change(screen.getByLabelText('现金最高比例 (%)'), { target: { value: '10' } })
  expect(screen.getByRole('checkbox', { name: '确认组合约束' })).not.toBeChecked()
  expect(screen.getByRole('alert')).toHaveTextContent('现金下限不能超过现金上限')
  fireEvent.click(screen.getByRole('checkbox', { name: '确认组合约束' }))
  expect(start).toBeDisabled()
})

it('applies a natural-language draft only after parsing, then requires confirmation', async () => {
  vi.spyOn(financialApi, 'parseConstraints').mockResolvedValue({ parser: 'rules', requires_confirmation: true,
    constraints: { max_weight_by_symbol: { MU: .15, CASH: .3 }, min_cash_weight: .2, max_equity_weight: .7, max_sector_weight: {} },
    recognized: ['MU不超过15%', '现金20%–30%'], unresolved: [] })
  render(<FinancialWorkflow workflow="portfolio" mode="auto" />)
  fireEvent.change(screen.getByLabelText('用自然语言描述'), { target: { value: 'MU不超过15%，现金20%–30%' } })
  expect(screen.getByRole('checkbox', { name: '确认组合约束' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: '解析为约束草稿' }))
  await screen.findByText('解析结果 · 待核对')
  expect(screen.getByRole('button', { name: '开始 portfolio 合成演示' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: '将草稿填入表单' }))
  expect(screen.getByLabelText('现金最高比例 (%)')).toHaveValue(30)
  fireEvent.click(screen.getByRole('checkbox', { name: '确认组合约束' }))
  expect(screen.getByRole('button', { name: '开始 portfolio 合成演示' })).toBeEnabled()
  fireEvent.change(screen.getByLabelText('用自然语言描述'), { target: { value: '稳健一点' } })
  expect(screen.getByRole('button', { name: '开始 portfolio 合成演示' })).toBeDisabled()
})

it('blocks unresolved clauses and permits explicit discard for manual entry', async () => {
  vi.spyOn(financialApi, 'parseConstraints').mockResolvedValue({ parser: 'rules', requires_confirmation: true,
    constraints: { max_weight_by_symbol: {}, min_cash_weight: 0, max_equity_weight: 1, max_sector_weight: {} },
    recognized: [], unresolved: ['请明确稳健的数值条件'] })
  render(<FinancialWorkflow workflow="portfolio" mode="review" />)
  fireEvent.change(screen.getByLabelText('用自然语言描述'), { target: { value: '稳健一点' } })
  fireEvent.click(screen.getByRole('button', { name: '解析为约束草稿' }))
  await screen.findByText('待澄清：请明确稳健的数值条件')
  expect(screen.getByRole('button', { name: '将草稿填入表单' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: '清除描述，手动填写' }))
  expect(screen.getByRole('checkbox', { name: '确认组合约束' })).toBeEnabled()
})

it('ignores late parsing responses after text changes', async () => {
  let resolve!: (v: Awaited<ReturnType<typeof financialApi.parseConstraints>>) => void
  vi.spyOn(financialApi, 'parseConstraints').mockReturnValue(new Promise(r => { resolve = r }))
  render(<FinancialWorkflow workflow="portfolio" mode="auto" />)
  fireEvent.change(screen.getByLabelText('用自然语言描述'), { target: { value: '现金至少20%' } })
  fireEvent.click(screen.getByRole('button', { name: '解析为约束草稿' }))
  fireEvent.change(screen.getByLabelText('用自然语言描述'), { target: { value: '现金至少40%' } })
  resolve({ parser: 'rules', requires_confirmation: true, constraints: { max_weight_by_symbol: {}, min_cash_weight: .2, max_equity_weight: 1, max_sector_weight: {} }, recognized: ['现金至少20%'], unresolved: [] })
  await waitFor(() => expect(screen.queryByText('解析结果 · 待核对')).not.toBeInTheDocument())
  expect(screen.getByRole('button', { name: '开始 portfolio 合成演示' })).toBeDisabled()
})

it('submits only a captured dataset id and confirmed constraints in live mode', async () => {
  vi.spyOn(financialApi, 'connection').mockResolvedValue({ configured: true, model: 'new-model', message: '已配置' })
  vi.spyOn(agentApi, 'createConversation').mockResolvedValue({ id: 'c', title: 'user' } as Awaited<ReturnType<typeof agentApi.createConversation>>)
  vi.spyOn(financialApi, 'prepare').mockResolvedValue({ dataset_id: 'dataset', conversation_id: 'c', as_of: '2026-10-11T00:00:00Z', snapshot_id: 'user-dataset', symbols: ['MU'], sectors: [], cash: '100', currency: 'USD', holdings: [{ symbol: 'MU', quantity: '1', price: '200', price_at: '2026-10-09T20:00:00Z', source: 'yahoo' }], limitations: ['行情可能延迟'] })
  const create = vi.spyOn(financialApi, 'create').mockResolvedValue({ schema_version: 1, conversation_id: 'c', correlation_id: 'corr', portfolio_run_id: 'p', runs: [{ run_id: 'p', mas_kind: 'portfolio_rebalance', status: 'queued', version: 1 }] })
  vi.spyOn(financialApi, 'getRun').mockResolvedValue({ schema_version: 1, run_id: 'p', conversation_id: 'c', correlation_id: 'corr', mas_kind: 'portfolio_rebalance', status: 'queued', mode: 'auto', version: 1, error_code: null, artifact: null, artifact_ref: null, validation_outcome: 'pending', limitations: [], data_source: 'user' })
  render(<FinancialWorkflow workflow="portfolio" mode="auto" />)
  fireEvent.change(screen.getByRole('combobox', { name: '金融数据来源' }), { target: { value: 'user' } })
  fireEvent.click(screen.getByRole('button', { name: '准备真实数据快照' }))
  await screen.findByText('行情可能延迟')
  const start = screen.getByRole('button', { name: '开始 portfolio 真实分析' })
  expect(start).toBeDisabled()
  fireEvent.click(screen.getByLabelText('已核对数据与价格时间，允许将此快照用于独立模型分析'))
  fireEvent.click(screen.getByRole('checkbox', { name: '确认组合约束' }))
  fireEvent.click(start)
  await waitFor(() => expect(create).toHaveBeenCalledTimes(1))
  const body = create.mock.calls[0][1]
  expect(body.dataset_id).toBe('dataset')
  expect(body.portfolio?.portfolio_snapshot_id).toBe('user-dataset')
  expect(body.portfolio?.user_constraints.min_cash_weight).toBe(.2)
  expect(body).not.toHaveProperty('holdings')
  expect(body).not.toHaveProperty('cash')
})
