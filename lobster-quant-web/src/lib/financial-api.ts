import { object, text, strings, statuses, validArtifact } from '@/types/financial-validation'
import { API_BASE_URL } from './constants'
import type { FinancialCreation, FinancialRun, WorkflowType, AllocationConstraints, FinancialRequest, ConstraintDraft, LivePrepared } from '@/types/financial-api'

export class FinancialRequestError extends Error {
  constructor(public status: number, message: string) { super(message) }
}
export function parseFinancialRun(value: unknown, expectedId?: string, expectedConversation?: string, expectedCorrelation?: string): FinancialRun {
  if (!object(value)) throw new Error('金融结果不是对象')
  const v = value
  const outcomes = v.mas_kind === 'market_investigation' ? ['verified', 'partial', 'insufficient_evidence', 'pending'] : ['feasible', 'infeasible', 'insufficient_data', 'pending']
  if (v.schema_version !== 1 || !['market_investigation', 'portfolio_rebalance'].includes(v.mas_kind as string)
    || !statuses.includes(v.status as string) || !outcomes.includes(v.validation_outcome as string)
    || !text(v.run_id) || !text(v.conversation_id) || !text(v.correlation_id) || !['auto', 'review'].includes(v.mode as string) || !Number.isInteger(v.version) || Number(v.version) < 1
    || !(v.error_code === null || typeof v.error_code === 'string') || !strings(v.limitations)
    || (v.data_source !== undefined && !['demo', 'user'].includes(v.data_source as string))
    || (expectedId !== undefined && v.run_id !== expectedId) || (expectedConversation !== undefined && v.conversation_id !== expectedConversation) || (expectedCorrelation !== undefined && v.correlation_id !== expectedCorrelation)
    || (v.artifact === null ? v.artifact_ref !== null || v.validation_outcome !== 'pending' : !object(v.artifact_ref) || v.artifact_ref.schema_version !== 1 || !text(v.artifact_ref.artifact_id) || !validArtifact(v.artifact, v.mas_kind as string, v.run_id as string, v.validation_outcome as string))) throw new Error('金融结果契约不匹配，请刷新或检查服务版本')
  return v as unknown as FinancialRun
}
export function parseFinancialCreation(value: unknown, workflow: Exclude<WorkflowType, 'general'>, conversationId: string): FinancialCreation {
  if (!object(value) || value.schema_version !== 1 || value.conversation_id !== conversationId || !text(value.correlation_id) || !Array.isArray(value.runs)) throw new Error('金融工作流契约不匹配')
  const expected = workflow === 'combined' ? ['market_investigation', 'portfolio_rebalance'] : [workflow === 'market' ? 'market_investigation' : 'portfolio_rebalance']
  const ids = new Set<string>()
  if (value.runs.length !== expected.length || !value.runs.every(run => {
    if (!object(run) || !text(run.run_id) || ids.has(run.run_id) || !expected.includes(run.mas_kind as string) || !statuses.includes(run.status as string) || !Number.isInteger(run.version) || Number(run.version) < 1) return false
    ids.add(run.run_id)
    return (run.mas_kind === 'market_investigation' ? value.market_run_id : value.portfolio_run_id) === run.run_id
  }) || new Set(value.runs.map(run => run.mas_kind)).size !== expected.length
    || (workflow === 'market' && value.portfolio_run_id != null) || (workflow === 'portfolio' && value.market_run_id != null)) throw new Error('金融工作流返回了无效运行 ID')
  return value as unknown as FinancialCreation
}
async function request(path: string, body?: unknown): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/financial${path}`, { method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}) })
  const value = await response.json().catch(() => ({}))
  if (!response.ok) throw new FinancialRequestError(response.status, typeof value.detail === 'string' ? value.detail : value.error?.message ?? `请求失败 (${response.status})`)
  return value
}
export const defaultConstraints = (): AllocationConstraints => ({ max_weight_by_symbol: { MU: .25 }, min_cash_weight: .2, max_equity_weight: 1, max_sector_weight: {} })
export function demoRequest(workflow: Exclude<WorkflowType, 'general'>, conversationId: string, mode: 'review' | 'auto', symbol = 'MU', key = crypto.randomUUID(), constraints = defaultConstraints()): FinancialRequest {
  const as_of = '2026-09-29T20:05:00Z'
  return { conversation_id: conversationId, idempotency_key: key, mode,
    ...(workflow !== 'portfolio' ? { market: { symbol: symbol.trim().toUpperCase(), as_of, sector_benchmark: 'SOXX' } } : {}),
    ...(workflow !== 'market' ? { portfolio: { portfolio_snapshot_id: 'synthetic-mu-soxx-v1', as_of, user_constraints: constraints } } : {}) }
}
export const financialApi = {
  create: async (workflow: Exclude<WorkflowType, 'general'>, body: FinancialRequest) => {
    return parseFinancialCreation(await request(`/${{ market: 'market-investigations', portfolio: 'portfolio-reviews', combined: 'combined-reviews' }[workflow]}`, body), workflow, body.conversation_id)
  },
  getRun: async (id: string) => parseFinancialRun(await request(`/runs/${encodeURIComponent(id)}`), id),
  action: async (id: string, name: 'approve' | 'pause' | 'resume' | 'cancel', version: number) => parseFinancialRun(await request(`/runs/${encodeURIComponent(id)}/${name}`, { expected_version: version }), id),
  connection: async () => await request('/connection') as { configured: boolean; model: string; message: string },
  checkConnection: async () => await request('/connection/check', { check_model: true }) as { configured: boolean; model: string; message: string },
  prepare: async (body: { conversation_id: string; workflow: string; symbol: string; sector_benchmark?: string }) => await request('/live/prepare', body) as LivePrepared,
  parseConstraints: async (body: { text: string; symbols: string[]; sectors: string[]; use_llm: boolean }) => await request('/constraints/parse', body) as ConstraintDraft,
}
