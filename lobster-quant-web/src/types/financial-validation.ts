export const object = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v)
export const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
export const finite = (v: unknown) => typeof v === 'number' && Number.isFinite(v)
const nullableNumber = (v: unknown) => v === null || finite(v)
export const strings = (v: unknown) => Array.isArray(v) && v.every(item => typeof item === 'string')
const date = (v: unknown) => text(v) && Number.isFinite(Date.parse(v))
const nullableDate = (v: unknown) => v === null || date(v)
export const statuses = ['queued', 'executing', 'waiting_user', 'paused', 'completed', 'failed', 'cancelled', 'expired']
const risk = (v: unknown) => object(v) && text(v.tool_result_id) && ['volatility', 'maximum_drawdown', 'concentration', 'cash_weight'].every(key => nullableNumber(v[key]))
const weights = (v: unknown) => object(v) && Object.entries(v).every(([key, value]) => text(key) && finite(value))
export function validArtifact(v: unknown, kind: string, runId: string, outcome: string) {
  if (!object(v) || v.schema_version !== 1 || v.producing_run_id !== runId || v.status !== outcome || !date(v.as_of) || !strings(v.limitations)) return false
  if (kind === 'market_investigation') return !('snapshot_id' in v) && text(v.symbol)
    && Array.isArray(v.numeric_facts) && v.numeric_facts.every(f => object(f) && text(f.name) && finite(f.value) && text(f.unit) && text(f.evidence_id) && text(f.tool_result_id))
    && Array.isArray(v.hypotheses) && v.hypotheses.every(h => object(h) && text(h.explanation) && strings(h.support_ids) && strings(h.against_ids) && ['supported', 'contradicted', 'unverified'].includes(h.disposition as string))
    && Array.isArray(v.evidence) && v.evidence.every(e => object(e) && text(e.id) && ['market_tool', 'filing', 'news', 'macro', 'document'].includes(e.source_type as string) && text(e.source_locator) && nullableDate(e.published_at) && nullableDate(e.available_at) && date(e.observed_at) && text(e.content_hash) && (e.excerpt === null || typeof e.excerpt === 'string'))
  return !('symbol' in v) && text(v.snapshot_id) && weights(v.current_weights) && weights(v.proposed_weights)
    && object(v.constraint_check) && ['pass', 'fail', 'unknown'].includes(v.constraint_check.status as string) && strings(v.constraint_check.unknowns)
    && Array.isArray(v.constraint_check.violations) && v.constraint_check.violations.every(c => object(c) && text(c.constraint) && (c.symbol === null || text(c.symbol)) && nullableNumber(c.actual) && nullableNumber(c.limit) && text(c.reason))
    && (v.risk_comparison === null || (object(v.risk_comparison) && risk(v.risk_comparison.before) && risk(v.risk_comparison.after)))
    && (v.simulation === null || (object(v.simulation) && text(v.simulation.tool_result_id) && text(v.simulation.adjustment) && text(v.simulation.rebalance_cadence) && finite(v.simulation.fees_bps) && finite(v.simulation.slippage_bps) && nullableNumber(v.simulation.net_return) && strings(v.simulation.assumptions))) && strings(v.evidence_ids)
}
