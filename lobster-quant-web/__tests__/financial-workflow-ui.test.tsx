import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { FinancialWorkflow } from '@/components/financial/FinancialWorkflow'
import { financialApi } from '@/lib/financial-api'
import { agentApi } from '@/lib/agent-api'
vi.mock('@/hooks/useFinancialEvents', () => ({ useFinancialEvents: (id: string) => ({ events: [{ seq: 1, event_id: id, event_type: 'mas.review_required', payload: { role: 'Coordinator', status: 'waiting_user', prompt: 'private prompt' } }], cursor: 1, connection: 'connected' }) }))
vi.mock('@/lib/agent-api', () => ({ agentApi: { createConversation: vi.fn() } }))
vi.mock('@/lib/financial-api', async importOriginal => ({ ...await importOriginal<typeof import('@/lib/financial-api')>(), financialApi: { create: vi.fn(), getRun: vi.fn(), action: vi.fn() } }))
const snapshot = (id: string, kind: string) => ({ schema_version: 1 as const, run_id: id, conversation_id: 'c', correlation_id: 'pair', mas_kind: kind, status: 'waiting_user', mode: 'review', version: 1, artifact_ref: null, artifact: null, validation_outcome: 'pending' as const, error_code: null, limitations: [] })
beforeEach(() => { vi.clearAllMocks(); vi.mocked(agentApi.createConversation).mockResolvedValue({ id: 'c' }) })
afterEach(() => vi.restoreAllMocks())
describe('accessible financial workflow', () => {
  it('shows empty state, independent IDs/review controls and safe event summaries', async () => {
    vi.mocked(financialApi.create).mockResolvedValue({ schema_version: 1, conversation_id: 'c', correlation_id: 'pair', market_run_id: 'm', portfolio_run_id: 'p', runs: [{ run_id: 'm', mas_kind: 'market_investigation', status: 'waiting_user', version: 1 }, { run_id: 'p', mas_kind: 'portfolio_rebalance', status: 'waiting_user', version: 1 }] })
    vi.mocked(financialApi.getRun).mockImplementation(async id => snapshot(id, id === 'm' ? 'market_investigation' : 'portfolio_rebalance') as Awaited<ReturnType<typeof financialApi.getRun>>)
    render(<FinancialWorkflow workflow="combined" mode="review" />)
    expect(screen.getByRole('status')).toHaveTextContent('尚未启动')
    fireEvent.click(screen.getByRole('checkbox', { name: '确认组合约束' }))
    fireEvent.click(screen.getByRole('button', { name: '开始 combined 合成演示' }))
    await waitFor(() => expect(screen.getByRole('button', { name: '批准此 Market 分析' })).toBeEnabled())
    expect(screen.getByRole('button', { name: '批准此 Portfolio 分析' })).toBeDisabled()
    expect(screen.getByText('m')).toBeInTheDocument(); expect(screen.getByText('p')).toBeInTheDocument()
    expect(screen.queryByText(/private prompt/)).not.toBeInTheDocument()
    expect(screen.getAllByText(/Coordinator/)).toHaveLength(4)
    expect(financialApi.create).toHaveBeenCalledWith('combined', expect.objectContaining({ conversation_id: 'c', portfolio: expect.objectContaining({ portfolio_snapshot_id: 'synthetic-mu-soxx-v1' }) }))
  })
  it('shows creation error as accessible alert and keeps idempotency for retry', async () => {
    vi.mocked(financialApi.create).mockRejectedValue(new Error('server unavailable'))
    render(<FinancialWorkflow workflow="portfolio" mode="auto" />)
    fireEvent.click(screen.getByRole('checkbox', { name: '确认组合约束' }))
    fireEvent.click(screen.getByRole('button', { name: '开始 portfolio 合成演示' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('server unavailable')
    fireEvent.click(screen.getByRole('button', { name: '重试同一任务' }))
    await waitFor(() => expect(financialApi.create).toHaveBeenCalledTimes(2))
    expect(vi.mocked(financialApi.create).mock.calls[0][1]).toEqual(vi.mocked(financialApi.create).mock.calls[1][1])
  })
})
it('announces loading and renders terminal partial evidence with source citation and limitation', async () => {
  vi.mocked(financialApi.create).mockResolvedValue({ schema_version: 1, conversation_id: 'c', correlation_id: 'single', market_run_id: 'm', runs: [{ run_id: 'm', mas_kind: 'market_investigation', status: 'completed', version: 2 }] })
  let resolveRun!: (value: Awaited<ReturnType<typeof financialApi.getRun>>) => void
  vi.mocked(financialApi.getRun).mockReturnValue(new Promise(resolve => { resolveRun = resolve }))
  render(<FinancialWorkflow workflow="market" mode="auto" />)
  fireEvent.click(screen.getByRole('button', { name: '开始 market 合成演示' }))
  await waitFor(() => expect(screen.getByText(/正在读取结果/)).toBeInTheDocument())
  resolveRun({ ...snapshot('m', 'market_investigation'), correlation_id: 'single', mas_kind: 'market_investigation', status: 'completed', mode: 'auto', validation_outcome: 'partial', error_code: null, artifact_ref: { artifact_id: 'a', schema_version: 1 }, artifact: { schema_version: 1, producing_run_id: 'm', symbol: 'MU', as_of: '2026-09-29T20:05:00Z', numeric_facts: [], hypotheses: [], limitations: ['missing independent source'], status: 'partial', evidence: [{ id: 'e', source_type: 'news', source_locator: 'https://example.org/source', published_at: null, available_at: null, observed_at: '2026-09-29T20:05:00Z', content_hash: 'hash', excerpt: 'source excerpt' }] }, limitations: [] })
  expect(await screen.findByText('missing independent source')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'https://example.org/source' })).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByText(/部分结果/)).toBeInTheDocument()
})

it.each([['SYSTEM_UNAVAILABLE', true], ['market_evidence_unavailable', false]])('renders exact API limitation %s without inferring a system message', async (marker, explicit) => {
  vi.mocked(financialApi.create).mockResolvedValue({ schema_version: 1, conversation_id: 'c', correlation_id: 'pair', portfolio_run_id: 'p', runs: [{ run_id: 'p', mas_kind: 'portfolio_rebalance', status: 'waiting_user', version: 1 }] })
  vi.mocked(financialApi.getRun).mockResolvedValue({ ...snapshot('p', 'portfolio_rebalance'), mas_kind: 'portfolio_rebalance', status: 'waiting_user', mode: 'review', limitations: [marker] })
  render(<FinancialWorkflow workflow="portfolio" mode="review" />)
  fireEvent.click(screen.getByRole('checkbox', { name: '确认组合约束' }))
  fireEvent.click(screen.getByRole('button', { name: '开始 portfolio 合成演示' }))
  await waitFor(() => expect(screen.getByRole('button', { name: '批准此 Portfolio 分析' })).toBeEnabled())
  if (explicit) expect(screen.getByText(/SYSTEM_UNAVAILABLE：API 已确认持久化/)).toBeInTheDocument()
  else { expect(screen.queryByText(/SYSTEM_UNAVAILABLE/)).not.toBeInTheDocument(); expect(screen.getByText(/Market 证据未传递/)).toBeInTheDocument() }
})
