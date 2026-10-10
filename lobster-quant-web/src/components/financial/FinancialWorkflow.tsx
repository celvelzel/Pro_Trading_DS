'use client'
import { useEffect, useState } from 'react'
import { agentApi } from '@/lib/agent-api'
import { parseFinancialRun, demoRequest, financialApi, FinancialRequestError } from '@/lib/financial-api'
import { useFinancialEvents } from '@/hooks/useFinancialEvents'
import type { FinancialCreation, FinancialRun, WorkflowType } from '@/types/financial-api'
import type { PortfolioArtifact } from '@/types/financial-artifacts'
import { MarketResult } from './MarketResult'
import { PortfolioResult } from './PortfolioResult'
import { Button } from '@/components/ui/button'
const terminal = (status?: string) => ['completed', 'failed', 'cancelled', 'expired'].includes(status ?? '')
const safeFields = ['relation_id', 'relation_type', 'message_type', 'role', 'kind', 'action', 'status', 'evidence_ids', 'artifact_id', 'message_id', 'causation_id', 'sender_run_id', 'receiver_run_id', 'source_run_id', 'target_run_id']
export function eventSummary(payload: Record<string, unknown>) {
  return safeFields.flatMap(key => {
    const value = payload[key]
    if (typeof value === 'string') return [`${key}: ${value}`]
    if (Array.isArray(value) && value.every(v => typeof v === 'string')) return [`${key}: ${value.join(', ')}`]
    return []
  }).join(' · ')
}
export function PortfolioProvenance({ artifact }: { artifact: PortfolioArtifact }) {
  return <section aria-label="Portfolio 合成来源与计算记录" className="space-y-2 rounded border p-3">
    <h3 className="font-medium">Portfolio 合成来源与计算记录</h3>
    <p>合成数据来源。以下仅为已持久保存的计算引用；API 未暴露 provider URL 或外部引用。</p>
    <dl className="break-all text-sm"><dt>snapshot_id</dt><dd>{artifact.snapshot_id}</dd><dt>as_of</dt><dd>{artifact.as_of}</dd><dt>producing_run_id</dt><dd>{artifact.producing_run_id}</dd>
      <dt>调整前风险 tool_result_id</dt><dd>{artifact.risk_comparison?.before.tool_result_id ?? '无持久引用'}</dd>
      <dt>调整后风险 tool_result_id</dt><dd>{artifact.risk_comparison?.after.tool_result_id ?? '无持久引用'}</dd>
      <dt>模拟 tool_result_id</dt><dd>{artifact.simulation?.tool_result_id ?? '无持久引用'}</dd></dl>
    <p>其他 evidence_ids：未分类的持久引用；不据此断言外部来源或跨 MAS 消费。</p>
    <ul>{artifact.evidence_ids.map(id => <li className="break-all text-sm" key={id}>{id}</li>)}</ul>
    <p>Combined Market 引用在独立 Market 结果中展示，不作为此板的 Portfolio 来源。</p>
  </section>
}
function FinancialRunPanel({ id, conversation, correlation, marketReady, onSnapshot }: { id: string; conversation: string; correlation: string; marketReady: boolean; onSnapshot: (run: FinancialRun) => void }) {
  const [run, setRun] = useState<FinancialRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const { events, cursor, connection } = useFinancialEvents(id)
  useEffect(() => {
    let disposed = false
    const refresh = async () => {
      try { const next = parseFinancialRun(await financialApi.getRun(id), id, conversation, correlation); if (!disposed) { setRun(next); onSnapshot(next); setError(null) } }
      catch (e) { if (!disposed) setError(e instanceof Error ? e.message : '结果读取失败') }
    }
    void refresh()
    const timer = setInterval(() => void refresh(), 1500)
    return () => { disposed = true; clearInterval(timer) }
  }, [id, conversation, correlation, onSnapshot])
  async function action(name: 'approve' | 'pause' | 'resume' | 'cancel') {
    if (!run) return
    setBusy(true); setError(null)
    try { const next = parseFinancialRun(await financialApi.action(id, name, run.version), id, conversation, correlation); setRun(next); onSnapshot(next) }
    catch (e) {
      setError(e instanceof FinancialRequestError && e.status === 409 ? '状态或审批顺序已变化，请等待刷新后重试；批准仅适用于本 run。' : e instanceof Error ? e.message : '操作失败')
      try { const next = parseFinancialRun(await financialApi.getRun(id), id, conversation, correlation); setRun(next); onSnapshot(next) } catch { /* polling retries */ }
    } finally { setBusy(false) }
  }
  const blocked = run?.mas_kind === 'portfolio_rebalance' && !marketReady
  return <article className="space-y-4 rounded-xl border p-4" aria-label={`${run?.mas_kind ?? 'Financial'} run ${id}`}>
    <h2 className="font-semibold">{run?.mas_kind === 'market_investigation' ? 'Market' : run?.mas_kind === 'portfolio_rebalance' ? 'Portfolio' : 'Financial'} Run</h2>
    <p className="break-all font-mono text-xs">{id}</p>
    <p role="status">{run ? `${run.status} · v${run.version} · ${run.validation_outcome}` : '正在读取结果…'} · SSE {connection} · cursor {cursor}</p>
    {error && <p role="alert">{error}</p>}
    {run?.status === 'waiting_user' && <><p>审阅合成数据分析；批准仅授权本 run 的研究与模拟。</p><Button disabled={busy || blocked} onClick={() => void action('approve')}>批准此 {run.mas_kind === 'market_investigation' ? 'Market' : 'Portfolio'} 分析</Button>{blocked && <p>等待 Market 完成独立审阅和执行后再批准 Portfolio。</p>}</>}
    {run?.status === 'paused' && <Button disabled={busy} onClick={() => void action('resume')}>恢复此分析</Button>}
    {run?.status === 'executing' && <Button disabled={busy} onClick={() => void action('pause')}>暂停此分析</Button>}
    {run && !terminal(run.status) && <Button variant="outline" disabled={busy} onClick={() => void action('cancel')}>取消此 run</Button>}
    {run?.error_code && <p role="alert">{run.error_code}</p>}
    {run?.limitations.map((text, i) => <p key={i}>{text === 'SYSTEM_UNAVAILABLE' ? 'SYSTEM_UNAVAILABLE：API 已确认持久化的跨 MAS 不可用消息；Portfolio 未收到可用的 Market 证据。' : text === 'market_evidence_unavailable' ? 'Market 证据未传递到 Portfolio；组合结论受此限制。' : text}</p>)}
    <section aria-label="角色与证据轨迹"><h3 className="font-medium">角色与证据轨迹</h3>{!events.length && <p>等待运行事件。</p>}<ol className="space-y-2">{events.map(event => <li key={event.event_id} className="break-all text-xs"><span>{event.seq} · {typeof event.payload.role === 'string' ? event.payload.role : 'stage/system'} · {event.event_type}</span><p>{eventSummary(event.payload)}</p></li>)}</ol></section>
    {run?.mas_kind === 'portfolio_rebalance' && run.artifact && <PortfolioProvenance artifact={run.artifact} />}
    {run?.mas_kind === 'market_investigation' ? <MarketResult artifact={run.artifact} sourceProfile="demo" loading={!terminal(run.status)} /> : <PortfolioResult artifact={run?.artifact} sourceProfile="demo" loading={!run || !terminal(run.status)}  />}
  </article>
}
export function FinancialWorkflow({ workflow, mode, symbol: initialSymbol = 'MU' }: { workflow: Exclude<WorkflowType, 'general'>; mode: 'review' | 'auto'; symbol?: string }) {
  const [symbol, setSymbol] = useState(initialSymbol)
  const [created, setCreated] = useState<FinancialCreation | null>(null)
  const [runs, setRuns] = useState<Record<string, FinancialRun>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState<{ body: ReturnType<typeof demoRequest> } | null>(null)
  const [onSnapshot] = useState(() => (run: FinancialRun) => setRuns(previous => ({ ...previous, [run.run_id]: run })))
  async function start() {
    setBusy(true); setError(null)
    try {
      const saved = attempt ?? { body: demoRequest(workflow, (await agentApi.createConversation('Financial synthetic demo')).id, mode, symbol) }
      setAttempt(saved)
      setCreated(await financialApi.create(workflow, saved.body))
    } catch (e) { setError(e instanceof Error ? e.message : '创建失败') }
    finally { setBusy(false) }
  }
  const market = created?.market_run_id ? runs[created.market_run_id] : undefined
  return <section className="space-y-4" aria-label="金融合成演示">
    <p>合成演示数据 · 只读研究与模拟 · 快照 synthetic-mu-soxx-v1 · 不读取或修改真实持仓与现金。</p>
    {workflow !== 'portfolio' && <label className="block">Market symbol <input aria-label="Market symbol" className="ml-3 rounded border p-2" value={symbol} disabled={!!attempt} onChange={e => setSymbol(e.target.value)} /></label>}
    {workflow === 'combined' && <p>Combined 使用快照内 MU 或 SOXX；Market 与 Portfolio 各自审阅、各自运行。</p>}
    <Button disabled={busy || !!created || !symbol.trim()} onClick={() => void start()}>{busy ? '正在创建…' : attempt ? '重试同一任务' : `开始 ${workflow} 合成演示`}</Button>
    {error && <p role="alert">{error}</p>}
    {!created && <p role="status">{busy ? '正在创建独立运行…' : '尚未启动金融分析。'}</p>}
    {created && <><p>执行模式以各 run 的持久状态为准；切换选择不会改变现有 run。</p><p className="break-all">Correlation: {created.correlation_id}</p><div className="grid gap-4 lg:grid-cols-2">{created.runs.map(item => <FinancialRunPanel key={item.run_id} id={item.run_id} conversation={created.conversation_id} correlation={created.correlation_id} marketReady={!created.market_run_id || terminal(market?.status)}  onSnapshot={onSnapshot} />)}</div></>}
  </section>
}
