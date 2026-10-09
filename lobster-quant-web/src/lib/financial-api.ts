import { API_BASE_URL } from './constants'
import type { FinancialCreation, FinancialRun, WorkflowType } from '@/types/financial-api'

export class FinancialRequestError extends Error {
  constructor(public status: number, message: string) { super(message) }
}
export function parseFinancialRun(value: unknown): FinancialRun {
  const v = value as FinancialRun
  const outcomes = v?.mas_kind === 'market_investigation' ? ['verified', 'partial', 'insufficient_evidence', 'pending'] : ['feasible', 'infeasible', 'insufficient_data', 'pending']
  if (!v || v.schema_version !== 1 || !['market_investigation', 'portfolio_rebalance'].includes(v.mas_kind)
    || !['queued', 'executing', 'waiting_user', 'paused', 'completed', 'failed', 'cancelled', 'expired'].includes(v.status)
    || !outcomes.includes(v.validation_outcome) || !v.run_id || typeof v.conversation_id !== 'string' || typeof v.correlation_id !== 'string' || !['auto', 'review'].includes(v.mode) || !Number.isInteger(v.version)
    || !Array.isArray(v.limitations) || !v.limitations.every(text => typeof text === 'string')
    || v.artifact === undefined || v.artifact_ref === undefined
    || (!!v.artifact !== !!v.artifact_ref)
    || (v.artifact_ref && (v.artifact_ref.schema_version !== 1 || typeof v.artifact_ref.artifact_id !== 'string'))
    || (v.artifact && (v.artifact.schema_version !== 1 || v.artifact.producing_run_id !== v.run_id || v.artifact.status !== v.validation_outcome))) {
    throw new Error('金融结果契约不匹配，请刷新或检查服务版本')
  }
  if (v.artifact) {
    const artifact = v.artifact
    const valid = typeof artifact.as_of === 'string' && Array.isArray(artifact.limitations) && (
      v.mas_kind === 'market_investigation'
        ? 'numeric_facts' in artifact && Array.isArray(artifact.numeric_facts) && Array.isArray(artifact.hypotheses) && Array.isArray(artifact.evidence)
        : 'constraint_check' in artifact && typeof artifact.current_weights === 'object' && typeof artifact.proposed_weights === 'object' && !!artifact.constraint_check && Array.isArray(artifact.constraint_check.violations) && Array.isArray(artifact.constraint_check.unknowns) && Array.isArray(artifact.evidence_ids))
    if (!valid) throw new Error('金融 artifact 类型不匹配')
  }
  return v
}
async function request(path: string, body?: unknown): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/financial${path}`, { method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}) })
  const value = await response.json().catch(() => ({}))
  if (!response.ok) throw new FinancialRequestError(response.status, typeof value.detail === 'string' ? value.detail : value.error?.message ?? `请求失败 (${response.status})`)
  return value
}
export function demoRequest(workflow: Exclude<WorkflowType, 'general'>, conversationId: string, mode: 'review' | 'auto', symbol = 'MU', key = crypto.randomUUID()) {
  const as_of = '2026-09-29T20:05:00Z'
  return { conversation_id: conversationId, idempotency_key: key, mode,
    ...(workflow !== 'portfolio' ? { market: { symbol: symbol.trim().toUpperCase(), as_of, sector_benchmark: 'SOXX' } } : {}),
    ...(workflow !== 'market' ? { portfolio: { portfolio_snapshot_id: 'synthetic-mu-soxx-v1', as_of, user_constraints: { max_weight_by_symbol: { MU: .25 }, min_cash_weight: .2 } } } : {}) }
}
export const financialApi = {
  create: async (workflow: Exclude<WorkflowType, 'general'>, body: ReturnType<typeof demoRequest>) => {
    const v = await request(`/${{ market: 'market-investigations', portfolio: 'portfolio-reviews', combined: 'combined-reviews' }[workflow]}`, body) as FinancialCreation
    const ids = v.runs?.map(r => r.run_id)
    if (v.schema_version !== 1 || !ids?.length || new Set(ids).size !== ids.length || ids.length !== (workflow === 'combined' ? 2 : 1)) throw new Error('金融工作流返回了无效运行 ID')
    return v
  },
  getRun: async (id: string) => parseFinancialRun(await request(`/runs/${encodeURIComponent(id)}`)),
  action: async (id: string, name: 'approve' | 'pause' | 'resume' | 'cancel', version: number) => parseFinancialRun(await request(`/runs/${encodeURIComponent(id)}/${name}`, { expected_version: version })),
}
