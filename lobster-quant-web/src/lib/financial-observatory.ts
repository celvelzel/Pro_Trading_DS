// 金融 MAS 观测台：从持久事件/关系推导可视化视图模型（纯函数，无副作用）
import type { AgentEvent } from '@/lib/agent-types'

export type EventCategory = 'phase' | 'specialist' | 'tool' | 'budget' | 'cross' | 'intervention' | 'system'
export const EVENT_CATEGORIES: { key: EventCategory; label: string }[] = [
  { key: 'phase', label: '阶段' }, { key: 'specialist', label: '角色' }, { key: 'tool', label: '工具' },
  { key: 'budget', label: '预算' }, { key: 'cross', label: '跨MAS' }, { key: 'intervention', label: '干预' }, { key: 'system', label: '系统' },
]
const PHASE_EVENTS = new Set(['mas.checkpoint', 'mas.handoff', 'mas.challenge', 'mas.replan', 'mas.coordination',
  'mas.approval_recommendation', 'mas.revision_request', 'mas.verdict'])
const INTERVENTION_EVENTS = new Set(['mas.approve', 'mas.pause', 'mas.resume', 'mas.cancel'])

export function categorizeEvent(type: string, payload: Record<string, unknown>): EventCategory {
  if (type.startsWith('cross_mas.')) return 'cross'
  if (PHASE_EVENTS.has(type)) return 'phase'
  if (INTERVENTION_EVENTS.has(type)) return 'intervention'
  if (type === 'mas.invoked' || type === 'mas.returned' || type === 'mas.invocation_failed')
    return payload.kind === 'tool' ? 'tool' : 'specialist'
  if (type === 'mas.budget_reserved') return 'budget'
  return 'system'
}

// 摘要白名单：模型散文/提示词等未知字段永不进入界面
const SAFE_SUMMARY_FIELDS = ['relation_id', 'relation_type', 'message_type', 'role', 'kind', 'action', 'status',
  'evidence_ids', 'artifact_id', 'message_id', 'causation_id', 'sender_run_id', 'receiver_run_id',
  'source_run_id', 'target_run_id'] as const
export function eventSafeSummary(payload: Record<string, unknown>): string {
  return SAFE_SUMMARY_FIELDS.flatMap(key => {
    const value = payload[key]
    if (typeof value === 'string') return [`${key}: ${value}`]
    if (Array.isArray(value) && value.every(v => typeof v === 'string')) return [`${key}: ${value.join(', ')}`]
    return []
  }).join(' · ')
}

// 详情白名单：未知字段（如模型提示词）永不渲染
export const DETAIL_FIELDS = ['relation_id', 'relation_type', 'message_type', 'message_id', 'causation_id',
  'role', 'kind', 'action', 'status', 'phase', 'invocation_key', 'counter', 'reserved_counters',
  'missing_checks', 'evidence_ids', 'artifact_id', 'code', 'parent_run_id', 'target_run_id',
  'source_run_id', 'sender_run_id', 'receiver_run_id', 'tool_result_id', 'tool_name'] as const

export interface TimelineItem { event: AgentEvent; category: EventCategory }

export function deriveTimeline(events: AgentEvent[], filter: EventCategory | 'all' = 'all'): TimelineItem[] {
  return events
    .map(event => ({ event, category: categorizeEvent(event.event_type, event.payload) }))
    .filter(item => filter === 'all' || item.category === filter)
}

// —— 流程 Pipeline ——
export type StageStatus = 'done' | 'active' | 'pending'
export interface PipelineStage { key: string; label: string; status: StageStatus; detail: string }

type EventMatch = (event: AgentEvent) => boolean
const phaseIs = (...prefixes: string[]): EventMatch => event =>
  typeof event.payload.phase === 'string' && prefixes.some(p => (event.payload.phase as string).startsWith(p))
const invocationStarts = (...prefixes: string[]): EventMatch => event =>
  typeof event.payload.invocation_key === 'string' && prefixes.some(p => (event.payload.invocation_key as string).startsWith(p))
const invokedWith = (kinds: string[], roles: string[]): EventMatch => event =>
  event.event_type === 'mas.invoked' && kinds.includes(event.payload.kind as string) && roles.includes(String(event.payload.role))
const eventTypeIs = (...types: string[]): EventMatch => event => types.includes(event.event_type)

const MARKET_STAGES: { key: string; label: string; match: EventMatch }[] = [
  { key: 'prepare', label: '调查准备', match: e => phaseIs('investigate', 'initial_tool')(e) || invocationStarts('market:initial')(e) },
  { key: 'specialists', label: '专家会审', match: e => phaseIs('role:')(e) || invocationStarts('sector:initial', 'events:initial')(e) },
  { key: 'review', label: '自适应复议', match: e => phaseIs('round:', 'check:', 'coordinate:', 'critique:')(e) },
  { key: 'complete', label: '结论', match: e => phaseIs('complete')(e) || eventTypeIs('mas.completed')(e) },
]
const PORTFOLIO_STAGES: { key: string; label: string; match: EventMatch }[] = [
  { key: 'baseline', label: '快照与风险基线', match: invocationStarts('snapshot:', 'risk:current:') },
  { key: 'candidates', label: '候选生成', match: invocationStarts('candidates:') },
  { key: 'proposal', label: '提案与约束校验', match: e => invocationStarts('opportunity:', 'coordinator:', 'check:', 'simulation:', 'risk:proposed:')(e) || phaseIs('round0', 'revision_ready', 'round1')(e) },
  { key: 'review', label: '独立评审', match: invokedWith(['model'], ['risk', 'constraint']) },
  { key: 'verdict', label: '验证与结论', match: e => invokedWith(['model'], ['verifier'])(e) || phaseIs('final')(e) || eventTypeIs('mas.completed')(e) },
]

export function derivePipeline(events: AgentEvent[], masKind: 'market_investigation' | 'portfolio_rebalance'): PipelineStage[] {
  const stages = masKind === 'market_investigation' ? MARKET_STAGES : PORTFOLIO_STAGES
  const reached = stages.map(stage => events.some(stage.match))
  const last = reached.lastIndexOf(true)
  return stages.map((stage, index) => ({
    key: stage.key,
    label: stage.label,
    status: index < last ? 'done' : index === last ? 'active' : 'pending',
    detail: index <= last ? `第 ${events.filter(stage.match).length} 条相关事件` : '尚未到达',
  }))
}

// —— 角色协作 ——
export interface AgentRow {
  role: string; tools: string[]; modelCalls: number; toolCalls: number
  lastAction: string | null; missingChecks: string[]; active: boolean
}
const MARKET_ROLES: { role: string; tools: string[] }[] = [
  { role: 'coordinator', tools: ['calculate_market_anomaly'] },
  { role: 'price_volume', tools: ['get_market_history', 'calculate_market_anomaly'] },
  { role: 'macro_sector', tools: ['calculate_market_anomaly', 'get_event_evidence'] },
  { role: 'event', tools: ['get_event_evidence'] },
  { role: 'critic', tools: [] },
]
const PORTFOLIO_ROLES: { role: string; tools: string[] }[] = [
  { role: 'coordinator', tools: ['get_portfolio_snapshot', 'generate_feasible_candidates', 'simulate_allocation'] },
  { role: 'opportunity', tools: ['generate_feasible_candidates'] },
  { role: 'risk', tools: ['calculate_portfolio_risk'] },
  { role: 'constraint', tools: ['validate_allocation'] },
  { role: 'verifier', tools: [] },
]

export function deriveAgents(events: AgentEvent[], masKind: 'market_investigation' | 'portfolio_rebalance'): AgentRow[] {
  const specs = masKind === 'market_investigation' ? MARKET_ROLES : PORTFOLIO_ROLES
  return specs.map(({ role, tools }) => {
    const own = events.filter(e => String(e.payload.role ?? '').toLowerCase() === role)
    const returned = own.filter(e => e.event_type === 'mas.returned' && e.payload.kind === 'model')
    const actions = returned.map(e => e.payload.action).filter((v): v is string => typeof v === 'string')
    const missing = returned.flatMap(e => Array.isArray(e.payload.missing_checks) ? e.payload.missing_checks as string[] : [])
    return {
      role, tools,
      modelCalls: own.filter(e => e.event_type === 'mas.invoked' && e.payload.kind === 'model').length,
      toolCalls: own.filter(e => e.event_type === 'mas.invoked' && e.payload.kind === 'tool').length,
      lastAction: actions.length ? actions[actions.length - 1] : null,
      missingChecks: [...new Set(missing)],
      active: own.length > 0,
    }
  })
}

// —— 预算（契约上限 RunBudget: 16/20/3）——
export interface BudgetUsage { modelCalls: number; toolCalls: number; rounds: number; maxModelCalls: 16; maxToolCalls: 20; maxRounds: 3 }
export function deriveBudget(events: AgentEvent[]): BudgetUsage {
  return {
    modelCalls: events.filter(e => e.event_type === 'mas.invoked' && e.payload.kind === 'model').length,
    toolCalls: events.filter(e => e.event_type === 'mas.invoked' && e.payload.kind === 'tool').length,
    rounds: events.filter(e => e.event_type === 'mas.budget_reserved' && e.payload.counter === 'rounds').length,
    maxModelCalls: 16, maxToolCalls: 20, maxRounds: 3,
  }
}

// —— 跨 MAS 消息流 ——
export interface CrossMessage {
  relationId: string; relationType: string; direction: 'out' | 'in'; peerRunId: string
  messageType: string | null; messageId: string | null; causationId: string | null
  deadlineAt: string | null; payloadArtifactId: string | null; createdAt: string | null
  delivered: boolean
}
const MESSAGE_TYPES = new Set(['MARKET_EVIDENCE_REQUEST', 'MARKET_EVIDENCE_READY', 'PORTFOLIO_IMPACT_REQUEST', 'SYSTEM_UNAVAILABLE'])

export function parseRelations(value: unknown, runId: string): CrossMessage[] {
  if (!value || typeof value !== 'object' || !Array.isArray((value as { relations?: unknown }).relations)) throw new Error('关系数据契约不匹配')
  return ((value as { relations: unknown[] }).relations).flatMap(raw => {
    const r = raw as Record<string, unknown>
    const envelope = (r.envelope ?? {}) as Record<string, unknown>
    const relationType = typeof r.relation_type === 'string' ? r.relation_type : ''
    const source = typeof r.source_run_id === 'string' ? r.source_run_id : ''
    const target = typeof r.target_run_id === 'string' ? r.target_run_id : ''
    if (!relationType || !source || !target) return []
    const rawType = typeof envelope.message_type === 'string' ? envelope.message_type : null
    return [{
      relationId: typeof r.relation_id === 'string' ? r.relation_id : '',
      relationType,
      direction: source === runId ? 'out' as const : 'in' as const,
      peerRunId: source === runId ? target : source,
      messageType: rawType && MESSAGE_TYPES.has(rawType) ? rawType : null,
      messageId: typeof envelope.message_id === 'string' ? envelope.message_id : null,
      causationId: typeof envelope.causation_id === 'string' ? envelope.causation_id : null,
      deadlineAt: typeof envelope.deadline_at === 'string' ? envelope.deadline_at : null,
      payloadArtifactId: typeof (envelope.payload_ref as Record<string, unknown> | null)?.artifact_id === 'string'
        ? (envelope.payload_ref as Record<string, unknown>).artifact_id as string : null,
      createdAt: typeof envelope.created_at === 'string' ? envelope.created_at : null,
      delivered: relationType === 'cross_admitted',
    }]
  })
}
