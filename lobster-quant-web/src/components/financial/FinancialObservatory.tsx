'use client'
// 金融 MAS 观测台：审计时间线 / 流程阶段 / 角色协作 / 跨 MAS 消息流
import { useEffect, useMemo, useState } from 'react'
import type { AgentEvent } from '@/lib/agent-types'
import type { FinancialRun } from '@/types/financial-api'
import type { MarketArtifact } from '@/types/financial-artifacts'
import { financialApi } from '@/lib/financial-api'
import {
  DETAIL_FIELDS, EVENT_CATEGORIES, categorizeEvent, deriveAgents, deriveBudget,
  derivePipeline, deriveTimeline, eventSafeSummary,
  type CrossMessage, type EventCategory,
} from '@/lib/financial-observatory'

const CATEGORY_STYLE: Record<EventCategory, string> = {
  phase: 'border-emerald-500/60 text-emerald-400',
  specialist: 'border-sky-500/60 text-sky-400',
  tool: 'border-violet-500/60 text-violet-400',
  budget: 'border-amber-500/60 text-amber-400',
  cross: 'border-cyan-500/60 text-cyan-400',
  intervention: 'border-orange-500/60 text-orange-400',
  system: 'border-border text-muted-foreground',
}
const STAGE_STYLE = { done: 'border-emerald-500/70 bg-emerald-500/10 text-emerald-300', active: 'border-sky-400 bg-sky-400/15 text-sky-200 ring-2 ring-sky-400/40', pending: 'border-dashed border-border text-muted-foreground' } as const

function StatusDot({ status }: { status: 'done' | 'active' | 'pending' }) {
  return <span aria-hidden="true" className={
    status === 'done' ? 'inline-block size-2 rounded-full bg-emerald-400'
      : status === 'active' ? 'inline-block size-2 rounded-full bg-sky-400 ring-2 ring-sky-400/40'
        : 'inline-block size-2 rounded-full border border-dashed border-muted-foreground'} />
}

function EventTimeline({ events }: { events: AgentEvent[] }) {
  const [filter, setFilter] = useState<EventCategory | 'all'>('all')
  const [open, setOpen] = useState<string | null>(null)
  const items = useMemo(() => deriveTimeline(events, filter), [events, filter])
  return <div className="space-y-2">
    <div className="flex flex-wrap gap-2" role="group" aria-label="事件类别过滤">
      <button type="button" aria-pressed={filter === 'all'} onClick={() => setFilter('all')}
        className={`rounded-full border px-2 py-0.5 text-xs ${filter === 'all' ? 'border-sky-400 text-sky-300' : 'border-border text-muted-foreground'}`}>全部 {events.length}</button>
      {EVENT_CATEGORIES.map(({ key, label }) => {
        const count = events.filter(e => categorizeEvent(e.event_type, e.payload) === key).length
        return <button key={key} type="button" aria-pressed={filter === key} onClick={() => setFilter(key)}
          className={`rounded-full border px-2 py-0.5 text-xs ${filter === key ? 'border-sky-400 text-sky-300' : CATEGORY_STYLE[key]}`}>{label} {count}</button>
      })}
    </div>
    {!items.length && <p className="text-sm text-muted-foreground">{events.length ? '该类别暂无事件。' : '等待运行事件。'}</p>}
    <ol className="space-y-2">
      {items.map(({ event, category }) => {
        const expanded = open === event.event_id
        const detail = DETAIL_FIELDS.flatMap(key => {
          const value = event.payload[key]
          if (typeof value === 'string') return [[key, value] as const]
          if (typeof value === 'number') return [[key, String(value)] as const]
          if (Array.isArray(value) && value.every(v => typeof v === 'string')) return [[key, value.join(', ')] as const]
          return []
        })
        return <li key={event.event_id} className="rounded border border-border/60">
          <button type="button" aria-expanded={expanded} onClick={() => setOpen(expanded ? null : event.event_id)}
            className="w-full space-y-1 p-2 text-left hover:bg-muted/40">
            <span className="block break-all text-xs">
              {event.seq} · {typeof event.payload.role === 'string' ? event.payload.role : 'stage/system'} · {event.event_type}
              <span aria-hidden="true"> · </span>
              <span className={`rounded-full border px-1.5 py-0.5 text-[10px] ${CATEGORY_STYLE[category]}`}>
                {EVENT_CATEGORIES.find(c => c.key === category)?.label}
              </span>
            </span>
            <p className="break-all text-xs text-muted-foreground">{eventSafeSummary(event.payload)}</p>
          </button>
          {expanded && <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-t border-border/60 p-2 text-xs">
            {detail.map(([key, value]) => <div key={key} className="contents"><dt className="font-mono text-muted-foreground">{key}</dt><dd className="break-all">{value}</dd></div>)}
            {!detail.length && <p className="text-muted-foreground">无白名单内字段；未渲染的字段（如模型提示词）不进入界面。</p>}
          </dl>}
        </li>
      })}
    </ol>
  </div>
}

function WorkflowPipeline({ events, masKind, terminal }: { events: AgentEvent[]; masKind: FinancialRun['mas_kind']; terminal: boolean }) {
  const stages = useMemo(() => derivePipeline(events, masKind), [events, masKind])
  return <div className="space-y-3">
    <ol className="flex flex-wrap items-center gap-2">
      {stages.map((stage, index) => <li key={stage.key} className="flex items-center gap-2">
        <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${STAGE_STYLE[stage.status]}`}>
          <StatusDot status={stage.status} />
          <span>{index + 1}. {stage.label}</span>
          <span className="text-[10px]">{stage.status === 'done' ? '已完成' : stage.status === 'active' ? (terminal ? '结束' : '进行中') : '未开始'}</span>
        </div>
        {index < stages.length - 1 && <span aria-hidden="true" className="text-muted-foreground">→</span>}
      </li>)}
    </ol>
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 text-xs text-muted-foreground">
      {stages.map(stage => <div key={stage.key} className="contents"><dt>{stage.label}</dt><dd>{stage.detail}</dd></div>)}
    </dl>
  </div>
}

function BudgetMeter({ label, value, max }: { label: string; value: number; max: number }) {
  const ratio = Math.min(1, max ? value / max : 0)
  return <div className="space-y-1">
    <p className="text-xs text-muted-foreground">{label} <span className="font-mono">{value}/{max}</span></p>
    <div className="h-2 w-full rounded-full bg-muted" role="img" aria-label={`${label} ${value}/${max}`}>
      <div className={`h-2 rounded-full ${ratio >= 1 ? 'bg-destructive' : ratio >= 0.75 ? 'bg-amber-400' : 'bg-emerald-400'}`} style={{ width: `${Math.max(4, ratio * 100)}%` }} />
    </div>
  </div>
}

function AgentBoard({ events, run }: { events: AgentEvent[]; run: FinancialRun }) {
  const agents = useMemo(() => deriveAgents(events, run.mas_kind), [events, run.mas_kind])
  const budget = useMemo(() => deriveBudget(events), [events])
  const hypotheses = run.mas_kind === 'market_investigation' ? (run.artifact as MarketArtifact | null)?.hypotheses ?? [] : []
  return <div className="space-y-4">
    <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
      {agents.map(agent => <article key={agent.role} className="space-y-1 rounded-lg border border-border/60 p-3" aria-label={`角色 ${agent.role}`}>
        <h4 className="flex items-center gap-2 font-mono text-sm">
          <StatusDot status={agent.active ? 'done' : 'pending'} />
          {agent.role}
          <span className="rounded-full border border-border px-1.5 text-[10px] text-muted-foreground">
            {agent.lastAction ? `末次动作 ${agent.lastAction}` : agent.active ? '已参与' : '未发言'}
          </span>
        </h4>
        <p className="text-xs text-muted-foreground">工具白名单：{agent.tools.length ? agent.tools.join(' / ') : '无（纯评审）'}</p>
        <p className="text-xs text-muted-foreground">模型调用 <span className="font-mono">{agent.modelCalls}</span> · 工具调用 <span className="font-mono">{agent.toolCalls}</span></p>
        {!!agent.missingChecks.length && <p className="text-xs text-amber-400">待补检查：{agent.missingChecks.join(', ')}</p>}
      </article>)}
    </div>
    <section aria-label="预算消耗" className="space-y-2 rounded-lg border border-border/60 p-3">
      <h4 className="text-sm font-medium">预算消耗（契约上限）</h4>
      <div className="grid gap-3 sm:grid-cols-3">
        <BudgetMeter label="模型调用" value={budget.modelCalls} max={budget.maxModelCalls} />
        <BudgetMeter label="工具调用" value={budget.toolCalls} max={budget.maxToolCalls} />
        <BudgetMeter label="协调轮次" value={budget.rounds} max={budget.maxRounds} />
      </div>
    </section>
    {run.mas_kind === 'market_investigation' && <section aria-label="假设记账" className="space-y-2 rounded-lg border border-border/60 p-3">
      <h4 className="text-sm font-medium">竞争性假设记账（结论恒为未证实）</h4>
      {!hypotheses.length && <p className="text-xs text-muted-foreground">尚无假设；假设在运行产出物中持久化。</p>}
      {!!hypotheses.length && <table className="w-full text-left text-xs">
        <thead><tr className="text-muted-foreground"><th className="p-1">解释（仅限四类）</th><th className="p-1">支持证据</th><th className="p-1">反对证据</th><th className="p-1">结论</th></tr></thead>
        <tbody>{hypotheses.map(h => <tr key={h.explanation} className="border-t border-border/60">
          <td className="p-1">{h.explanation}</td>
          <td className="p-1 font-mono">{h.support_ids.length}</td>
          <td className="p-1 font-mono">{h.against_ids.length}</td>
          <td className="p-1"><span className="rounded-full border border-amber-500/60 px-1.5 py-0.5 text-[10px] text-amber-400">unverified 未证实</span></td>
        </tr>)}</tbody>
      </table>}
    </section>}
  </div>
}

const MESSAGE_STYLE: Record<string, string> = {
  MARKET_EVIDENCE_REQUEST: 'border-sky-400/60 text-sky-300',
  MARKET_EVIDENCE_READY: 'border-emerald-400/60 text-emerald-300',
  PORTFOLIO_IMPACT_REQUEST: 'border-violet-400/60 text-violet-300',
  SYSTEM_UNAVAILABLE: 'border-destructive/80 text-red-400',
}

function CrossMasFlow({ runId }: { runId: string }) {
  const [messages, setMessages] = useState<CrossMessage[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let disposed = false
    const load = async () => {
      try {
        const list = financialApi.relations ? await financialApi.relations(runId) : []
        if (!disposed) { setMessages(list); setError(null) }
      } catch (e) { if (!disposed) setError(e instanceof Error ? e.message : '关系数据读取失败') }
    }
    void load()
    const timer = setInterval(() => void load(), 3000)
    return () => { disposed = true; clearInterval(timer) }
  }, [runId])
  if (error) return <p className="text-sm text-muted-foreground">{error}</p>
  if (!messages) return <p className="text-sm text-muted-foreground">正在读取跨 MAS 关系…</p>
  if (!messages.length) return <p className="text-sm text-muted-foreground">本 run 暂无跨 MAS 消息（独立运行不产生跨 MAS 通信；combined 运行将在此展示请求/证据/不可用消息）。</p>
  return <ol className="space-y-2">
    {messages.map(message => <li key={message.relationId} className={`rounded-lg border p-3 text-xs ${message.messageType ? MESSAGE_STYLE[message.messageType] ?? 'border-border' : 'border-border'}`}>
      <p className="flex flex-wrap items-center gap-2">
        <span aria-hidden="true" className="font-mono">{message.direction === 'out' ? '⟶ 发出' : '⟵ 收到'}</span>
        <span className={`rounded-full border px-1.5 py-0.5 ${message.messageType === 'SYSTEM_UNAVAILABLE' ? 'border-dashed border-destructive/80' : ''}`}>
          {message.messageType ?? message.relationType}
        </span>
        <span className="text-muted-foreground">{message.direction === 'out' ? '本 run → ' : ''}{message.peerRunId.slice(0, 12)}…</span>
        <span className={`text-[10px] ${message.delivered ? 'text-emerald-400' : 'text-amber-400'}`}>{message.delivered ? '已送达（准入通过）' : '配对关系'}</span>
      </p>
      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-muted-foreground">
        {message.messageId && <div className="contents"><dt>message_id</dt><dd className="break-all font-mono">{message.messageId}</dd></div>}
        {message.causationId && <div className="contents"><dt>causation</dt><dd className="break-all font-mono">因果链 → {message.causationId}</dd></div>}
        {message.payloadArtifactId && <div className="contents"><dt>payload</dt><dd className="break-all font-mono">artifact {message.payloadArtifactId}</dd></div>}
        {message.deadlineAt && <div className="contents"><dt>deadline</dt><dd>{message.deadlineAt}</dd></div>}
      </dl>
    </li>)}
  </ol>
}

const TABS = [
  { key: 'timeline', label: '审计时间线' }, { key: 'pipeline', label: '流程阶段' },
  { key: 'agents', label: '角色协作' }, { key: 'messages', label: '跨MAS消息流' },
] as const

export function FinancialObservatory({ run, events, terminal }: { run: FinancialRun; events: AgentEvent[]; terminal: boolean }) {
  const [tab, setTab] = useState<(typeof TABS)[number]['key']>('timeline')
  return <section aria-label="Agent 工作流观测台" className="space-y-3 rounded border border-border/60 p-3">
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="观测视图切换">
      <h3 className="mr-2 text-sm font-medium">Agent 工作流观测台</h3>
      {TABS.map(item => <button key={item.key} type="button" aria-pressed={tab === item.key} onClick={() => setTab(item.key)}
        className={`rounded-full border px-3 py-1 text-xs ${tab === item.key ? 'border-sky-400 text-sky-300' : 'border-border text-muted-foreground'}`}>{item.label}</button>)}
    </div>
    {tab === 'timeline' && <EventTimeline events={events} />}
    {tab === 'pipeline' && <WorkflowPipeline events={events} masKind={run.mas_kind} terminal={terminal} />}
    {tab === 'agents' && <AgentBoard events={events} run={run} />}
    {tab === 'messages' && <CrossMasFlow runId={run.run_id} />}
  </section>
}
