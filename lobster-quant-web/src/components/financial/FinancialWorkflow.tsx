'use client'
import { useEffect, useState } from 'react'
import { agentApi } from '@/lib/agent-api'
import { parseFinancialRun, demoRequest, financialApi, FinancialRequestError, defaultConstraints } from '@/lib/financial-api'
import { useFinancialEvents } from '@/hooks/useFinancialEvents'
import type { FinancialCreation, FinancialRun, WorkflowType, FinancialRequest, LivePrepared } from '@/types/financial-api'
import type { PortfolioArtifact } from '@/types/financial-artifacts'
import { MarketResult } from './MarketResult'
import { PortfolioResult } from './PortfolioResult'
import { Button } from '@/components/ui/button'
import { ConstraintsForm, constraintErrors } from './ConstraintsForm'
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
export function PortfolioProvenance({ artifact, source = 'demo' }: { artifact: PortfolioArtifact; source?: 'demo' | 'user' }) {
  const title = source === 'demo' ? 'Portfolio 合成来源与计算记录' : 'Portfolio 用户快照与计算记录'
  return <section aria-label={title} className="space-y-2 rounded border p-3">
    <h3 className="font-medium">{title}</h3>
    <p>{source === 'demo' ? '合成数据来源。' : '用户持仓与已捕获行情。'}以下仅为已持久保存的计算引用；API 未暴露 provider URL 或外部引用。</p>
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
    {run?.status === 'waiting_user' && <><p>审阅{run.data_source === 'user' ? '真实快照' : '合成数据'}分析；批准仅授权本 run 的研究与模拟。</p><Button disabled={busy || blocked} onClick={() => void action('approve')}>批准此 {run.mas_kind === 'market_investigation' ? 'Market' : 'Portfolio'} 分析</Button>{blocked && <p>等待 Market 完成独立审阅和执行后再批准 Portfolio。</p>}</>}
    {run?.status === 'paused' && <Button disabled={busy} onClick={() => void action('resume')}>恢复此分析</Button>}
    {run?.status === 'executing' && <Button disabled={busy} onClick={() => void action('pause')}>暂停此分析</Button>}
    {run && !terminal(run.status) && <Button variant="outline" disabled={busy} onClick={() => void action('cancel')}>取消此 run</Button>}
    {run?.error_code && <p role="alert">{run.error_code}</p>}
    {run?.limitations.map((text, i) => <p key={i}>{text === 'SYSTEM_UNAVAILABLE' ? 'SYSTEM_UNAVAILABLE：API 已确认持久化的跨 MAS 不可用消息；Portfolio 未收到可用的 Market 证据。' : text === 'market_evidence_unavailable' ? 'Market 证据未传递到 Portfolio；组合结论受此限制。' : text}</p>)}
    <section aria-label="角色与证据轨迹"><h3 className="font-medium">角色与证据轨迹</h3>{!events.length && <p>等待运行事件。</p>}<ol className="space-y-2">{events.map(event => <li key={event.event_id} className="break-all text-xs"><span>{event.seq} · {typeof event.payload.role === 'string' ? event.payload.role : 'stage/system'} · {event.event_type}</span><p>{eventSummary(event.payload)}</p></li>)}</ol></section>
    {run?.mas_kind === 'portfolio_rebalance' && run.artifact && <PortfolioProvenance artifact={run.artifact} source={run.data_source ?? 'demo'} />}
    {run?.mas_kind === 'market_investigation' ? <MarketResult artifact={run.artifact} sourceProfile={run.data_source ?? 'demo'} loading={!terminal(run.status)} /> : <PortfolioResult artifact={run?.artifact} sourceProfile={run?.data_source ?? 'demo'} loading={!run || !terminal(run.status)}  />}
  </article>
}
export function FinancialWorkflow({ workflow, mode, symbol: initialSymbol = 'MU' }: { workflow: Exclude<WorkflowType, 'general'>; mode: 'review' | 'auto'; symbol?: string }) {
  const [symbol, setSymbol] = useState(initialSymbol)
  const [created, setCreated] = useState<FinancialCreation | null>(null)
  const [runs, setRuns] = useState<Record<string, FinancialRun>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState<{ body: FinancialRequest } | null>(null)
  const [source, setSource] = useState<'demo' | 'user'>('demo')
  const [prepared, setPrepared] = useState<LivePrepared | null>(null)
  const [preparing, setPreparing] = useState(false)
  const [connection, setConnection] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const [benchmark, setBenchmark] = useState('')
  const [constraints, setConstraints] = useState(defaultConstraints)
  const [confirmed, setConfirmed] = useState(false)
  const [dataConfirmed, setDataConfirmed] = useState(false)
  const [naturalPending, setNaturalPending] = useState(false)
  const [onSnapshot] = useState(() => (run: FinancialRun) => setRuns(previous => ({ ...previous, [run.run_id]: run })))
  const symbols = prepared?.symbols ?? (source === 'demo' ? ['MU', 'SOXX', 'SPY', 'TLT'] : [])
  const sectors = prepared?.sectors ?? (source === 'demo' ? ['TECH', 'BROAD', 'BOND'] : [])
  const ready = (workflow === 'market' || (confirmed && !naturalPending && !constraintErrors(constraints, symbols).length))
    && (source === 'demo' || (prepared && dataConfirmed))
  async function prepare() {
    setPreparing(true); setError(null); setPrepared(null); setDataConfirmed(false); setConfirmed(false); setNaturalPending(false)
    try {
      const conversation = await agentApi.createConversation('Financial user snapshot')
      setPrepared(await financialApi.prepare({ conversation_id: conversation.id, workflow, symbol,
        ...(benchmark.trim() && workflow !== 'portfolio' ? { sector_benchmark: benchmark.trim().toUpperCase() } : {}) }))
    } catch (e) { setError(e instanceof Error ? e.message : '准备真实数据失败') }
    finally { setPreparing(false) }
  }
  async function check() {
    setChecking(true); setError(null)
    try { setConnection((await financialApi.checkConnection()).message) }
    catch (e) { setError(e instanceof Error ? e.message : '连接失败') }
    finally { setChecking(false) }
  }
  async function start() {
    setBusy(true); setError(null)
    try {
      if (!attempt && !ready) throw new Error('请先核对数据来源和组合约束。')
      let body: FinancialRequest
      if (prepared && source === 'user') {
        body = { conversation_id: prepared.conversation_id, dataset_id: prepared.dataset_id,
          idempotency_key: crypto.randomUUID(), mode,
          ...(workflow !== 'portfolio' ? { market: { symbol: symbol.trim().toUpperCase(), as_of: prepared.as_of,
            ...(benchmark.trim() ? { sector_benchmark: benchmark.trim().toUpperCase() } : {}) } } : {}),
          ...(workflow !== 'market' ? { portfolio: { portfolio_snapshot_id: prepared.snapshot_id!, as_of: prepared.as_of, user_constraints: constraints } } : {}) }
      } else body = attempt?.body ?? demoRequest(workflow, (await agentApi.createConversation('Financial synthetic demo')).id, mode, symbol, crypto.randomUUID(), constraints)
      const saved = attempt ?? { body }
      setAttempt(saved)
      setCreated(await financialApi.create(workflow, saved.body))
    } catch (e) { setError(e instanceof Error ? e.message : '创建失败') }
    finally { setBusy(false) }
  }
  const market = created?.market_run_id ? runs[created.market_run_id] : undefined
  return <section className="space-y-5" aria-label="金融研究工作流">
    <div className="space-y-3 rounded-xl border bg-card p-5">
      <label className="block text-sm font-medium">数据来源<select aria-label="金融数据来源" value={source} disabled={busy || !!attempt || preparing} onChange={e => { const next = e.target.value as 'demo' | 'user'; setSource(next); setPrepared(null); setConfirmed(false); setDataConfirmed(false); setNaturalPending(false); setError(null); setConnection(null); if (next === 'user') void financialApi.connection().then(v => setConnection(v.message)).catch(() => setConnection('无法读取连接配置。')); setConstraints(next === 'demo' ? defaultConstraints() : { max_weight_by_symbol: {}, min_cash_weight: .2, max_equity_weight: 1, max_sector_weight: {} }) }} className="ml-3 rounded border bg-background p-2"><option value="demo">合成演示</option><option value="user">我的美股持仓 / 最新行情</option></select></label>
      <p className="text-sm text-muted-foreground">{source === 'demo' ? '合成演示数据 · 快照 synthetic-mu-soxx-v1 · 不读取或修改真实持仓与现金。' : '真实 LLM + Yahoo 最新可用行情 + 已保存的 USD 持仓。仅创建研究快照，不修改持仓或下单。'}</p>
      {source === 'user' && <><p className="text-xs text-muted-foreground">先填写独立 financial-mas.json 配置；行情可能延迟，日线分析使用已收盘交易日。准备数据会向行情服务查询标的；开始运行后，快照和约束将发送到你配置的模型。</p><Button variant="outline" disabled={checking || preparing || !!attempt} onClick={() => void check()}>{checking ? '正在检查…' : '测试独立模型连接'}</Button>{connection && <p role="status" className="text-sm">{connection}</p>}</>}
    </div>
    {workflow !== 'portfolio' && <div className="flex flex-wrap items-end gap-4"><label className="block text-sm">Market symbol <input aria-label="Market symbol" className="ml-3 rounded border bg-background p-2" value={symbol} disabled={busy || !!attempt || preparing} onChange={e => { setSymbol(e.target.value); setPrepared(null); setDataConfirmed(false); setConfirmed(false); setNaturalPending(false) }} /></label>{source === 'user' && <label className="text-sm">行业基准（可选）<input aria-label="行业基准" value={benchmark} disabled={busy || !!attempt || preparing} onChange={e => { setBenchmark(e.target.value); setPrepared(null); setDataConfirmed(false); setConfirmed(false); setNaturalPending(false) }} className="ml-3 rounded border bg-background p-2" placeholder="例如 SOXX" /></label>}</div>}
    {workflow === 'combined' && <p className="text-sm text-muted-foreground">Combined 的 Market 标的须在{source === 'demo' ? '演示' : '你的'}快照中；Market 与 Portfolio 各自审阅、各自运行。</p>}
    {source === 'user' && <div className="space-y-3 rounded-xl border p-5"><Button variant="outline" disabled={preparing || !!attempt || !symbol.trim()} onClick={() => void prepare()}>{preparing ? '正在获取行情与快照…' : prepared ? '重新准备最新快照' : '准备真实数据快照'}</Button>
      {prepared && <><p className="text-sm">捕获时间：{prepared.as_of} · {prepared.currency} · 现金：{prepared.cash ?? '行情调查不使用持仓'}</p><div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">只读持仓快照</caption><thead><tr>{['标的','数量','估值价格','价格时间'].map(s => <th key={s} className="p-2">{s}</th>)}</tr></thead><tbody>{prepared.holdings.map(h => <tr key={h.symbol}><td className="p-2">{h.symbol}</td><td className="p-2">{h.quantity}</td><td className="p-2">{h.price}</td><td className="p-2">{h.price_at}</td></tr>)}</tbody></table></div>{prepared.limitations.map(s => <p key={s} className="text-xs text-muted-foreground">{s}</p>)}<label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={dataConfirmed} disabled={!!attempt} onChange={e => setDataConfirmed(e.target.checked)} />已核对数据与价格时间，允许将此快照用于独立模型分析</label></>}
    </div>}
    {workflow !== 'market' && <><ConstraintsForm key={`${source}-${prepared?.dataset_id ?? 'unprepared'}`} value={constraints} symbols={symbols} sectors={sectors} disabled={busy || !!attempt || preparing || (source === 'user' && !prepared)} onPending={setNaturalPending} onChange={next => { setConstraints(next); setConfirmed(false) }} /><label className="flex items-start gap-2 text-sm"><input type="checkbox" aria-label="确认组合约束" checked={confirmed} disabled={busy || !!attempt || naturalPending || (source === 'user' && !prepared)} onChange={e => setConfirmed(e.target.checked)} />已核对表单中的组合约束，按这些数值运行</label>{naturalPending && <p role="status" className="text-sm">自然语言描述尚未应用；请解析并填入表单，或清除描述后手动填写。</p>}</>}
    <Button disabled={busy || preparing || !!created || !symbol.trim() || (!attempt && !ready)} onClick={() => void start()}>{busy ? '正在创建…' : attempt ? '重试同一任务' : `开始 ${workflow} ${source === 'demo' ? '合成演示' : '真实分析'}`}</Button>
    {error && <p role="alert">{error}</p>}
    {!created && <p role="status">{busy ? '正在创建独立运行…' : '尚未启动金融分析。'}</p>}
    {created && <><p>执行模式以各 run 的持久状态为准；切换选择不会改变现有 run。</p><p className="break-all">Correlation: {created.correlation_id}</p><div className="grid gap-4 lg:grid-cols-2">{created.runs.map(item => <FinancialRunPanel key={item.run_id} id={item.run_id} conversation={created.conversation_id} correlation={created.correlation_id} marketReady={!created.market_run_id || terminal(market?.status)}  onSnapshot={onSnapshot} />)}</div></>}
    {created && created.runs.every(item => terminal(runs[item.run_id]?.status)) && <Button variant="outline" onClick={() => { setCreated(null); setAttempt(null); setRuns({}); setConfirmed(false); setDataConfirmed(false); setError(null) }}>新建研究任务</Button>}
  </section>
}
