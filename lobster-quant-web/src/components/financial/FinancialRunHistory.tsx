'use client'
// 金融 MAS 运行历史：只读列表（GET /api/financial/runs），支持 mas_kind/status/conversation 筛选与 run_id 关键字搜索；
// 点击条目展开 FinancialRunPanel 查看事件与 artifact。查看列表不会改变任何 run 状态。
import { useEffect, useMemo, useState } from 'react'
import { financialApi } from '@/lib/financial-api'
import type { FinancialRun, FinancialRunSummaryItem, FinancialStatus } from '@/types/financial-api'
import { FinancialRunPanel } from './FinancialWorkflow'
import { Button } from '@/components/ui/button'

const kindLabel = (kind: FinancialRunSummaryItem['mas_kind']) => kind === 'market_investigation' ? 'Market' : 'Portfolio'
const STATUS_LABEL: Record<FinancialStatus, string> = {
  queued: '排队中', executing: '执行中', waiting_user: '等待审批', paused: '已暂停',
  completed: '已完成', failed: '失败', cancelled: '已取消', expired: '已过期',
}
const STATUSES = Object.keys(STATUS_LABEL) as FinancialStatus[]
const shortId = (id: string) => id.length > 16 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id

export function FinancialRunHistory() {
  const [runs, setRuns] = useState<FinancialRunSummaryItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [refreshToken, setRefreshToken] = useState(0)
  const [masKind, setMasKind] = useState<'' | FinancialRunSummaryItem['mas_kind']>('')
  const [status, setStatus] = useState<'' | FinancialStatus>('')
  const [conversationId, setConversationId] = useState('')
  const [keyword, setKeyword] = useState('')
  const [copyState, setCopyState] = useState<{ id: string; ok: boolean } | null>(null)
  const [onSnapshot] = useState(() => (_run: FinancialRun) => {})
  useEffect(() => {
    let disposed = false
    const load = async () => {
      await Promise.resolve()
      if (disposed) return
      setLoading(true)
      try {
        const history = await financialApi.listRuns({
          conversationId: conversationId.trim() || undefined,
          masKind: masKind || undefined,
          status: status || undefined,
        })
        if (!disposed) { setRuns(history.runs); setError(null) }
      }
      catch (e) { if (!disposed) setError(e instanceof Error ? e.message : '运行历史读取失败') }
      finally { if (!disposed) setLoading(false) }
    }
    void load()
    return () => { disposed = true }
  }, [refreshToken, masKind, status, conversationId])
  const visible = useMemo(() => {
    const query = keyword.trim().toLowerCase()
    return query ? runs.filter(row => [row.run_id, row.conversation_id, row.correlation_id]
      .some(value => value.toLowerCase().includes(query))) : runs
  }, [runs, keyword])
  const hasFilters = Boolean(masKind || status || conversationId.trim() || keyword.trim())
  async function copyRunId(runId: string) {
    try {
      await navigator.clipboard.writeText(runId)
      setCopyState({ id: runId, ok: true })
    } catch { setCopyState({ id: runId, ok: false }) }
    window.setTimeout(() => setCopyState(current => (current?.id === runId ? null : current)), 2000)
  }
  return <section aria-label="金融 MAS 运行历史" className="space-y-4 rounded-xl border bg-card p-5">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="font-semibold">运行历史</h2>
      <Button variant="outline" disabled={loading} onClick={() => setRefreshToken(value => value + 1)}>刷新列表</Button>
    </div>
    <p className="text-sm text-muted-foreground">已持久化的金融 run 只读列表，按创建时间倒序（新的在前）；点击一条查看详情。查看列表不会改变任何 run 状态。</p>
    <div className="flex flex-wrap items-end gap-3" role="group" aria-label="运行历史筛选">
      <label className="flex min-w-36 flex-1 flex-col gap-1 text-xs text-muted-foreground">MAS 类型
        <select aria-label="按 MAS 类型筛选" value={masKind}
          onChange={event => setMasKind(event.target.value as '' | FinancialRunSummaryItem['mas_kind'])}
          className="rounded border border-border/60 bg-background px-2 py-1.5 text-sm text-foreground">
          <option value="">全部</option>
          <option value="market_investigation">Market（market_investigation）</option>
          <option value="portfolio_rebalance">Portfolio（portfolio_rebalance）</option>
        </select>
      </label>
      <label className="flex min-w-36 flex-1 flex-col gap-1 text-xs text-muted-foreground">状态
        <select aria-label="按状态筛选" value={status}
          onChange={event => setStatus(event.target.value as '' | FinancialStatus)}
          className="rounded border border-border/60 bg-background px-2 py-1.5 text-sm text-foreground">
          <option value="">全部</option>
          {STATUSES.map(value => <option key={value} value={value}>{STATUS_LABEL[value]}（{value}）</option>)}
        </select>
      </label>
      <label className="flex min-w-36 flex-1 flex-col gap-1 text-xs text-muted-foreground">conversation_id
        <input aria-label="按 conversation_id 筛选" value={conversationId}
          onChange={event => setConversationId(event.target.value)} placeholder="留空显示全部会话"
          className="rounded border border-border/60 bg-background px-2 py-1.5 text-sm text-foreground" />
      </label>
      <label className="flex min-w-36 flex-1 flex-col gap-1 text-xs text-muted-foreground">run_id / 关键字
        <input aria-label="按 run_id 或 correlation_id 搜索" value={keyword}
          onChange={event => setKeyword(event.target.value)} placeholder="前端即时过滤 run_id / correlation_id"
          className="rounded border border-border/60 bg-background px-2 py-1.5 text-sm text-foreground" />
      </label>
    </div>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">正在读取运行历史…</p>}
    {!loading && !visible.length && <p role="status">{hasFilters ? '没有符合当前筛选条件的运行记录。' : '暂无历史运行记录。'}</p>}
    {!!visible.length && <ul className="space-y-2">{visible.map(item => <li key={item.run_id} className="space-y-2">
      <div className="flex items-start gap-2">
        <button type="button" aria-pressed={selected === item.run_id} aria-label={`查看运行 ${item.run_id}`}
          onClick={() => setSelected(selected === item.run_id ? null : item.run_id)}
          className={`w-full min-w-0 flex-1 space-y-1 rounded border p-3 text-left hover:bg-muted/40 ${selected === item.run_id ? 'border-sky-400/60' : 'border-border/60'}`}>
          <span className="block text-sm">{kindLabel(item.mas_kind)} · {item.status} · v{item.version} · {item.validation_outcome}</span>
          <span className="block break-all font-mono text-xs" title={item.run_id}>{shortId(item.run_id)}</span>
          {item.error_code && <span className="block break-all text-xs text-destructive">error_code: {item.error_code}</span>}
          <span className="block break-all text-xs text-muted-foreground">as_of {item.as_of ?? '无'} · 创建 {item.created_at ?? '无'} · 更新 {item.updated_at ?? '无'}</span>
          <span className="block break-all text-xs text-muted-foreground">{item.conversation_id} · {item.correlation_id}</span>
        </button>
        <Button variant="outline" disabled={!!copyState && copyState.id === item.run_id && !copyState.ok} aria-label={`复制 run_id ${item.run_id}`}
          onClick={() => void copyRunId(item.run_id)}>复制</Button>
      </div>
      {copyState && copyState.id === item.run_id && <p role="status" className={copyState.ok ? 'text-xs text-success' : 'text-xs text-destructive'}>
        {copyState.ok ? 'run_id 已复制。' : '复制失败，请手动选择完整 run_id。'}
      </p>}
      {selected === item.run_id && <FinancialRunPanel id={item.run_id} conversation={item.conversation_id}
        correlation={item.correlation_id} onSnapshot={onSnapshot} />}
    </li>)}</ul>}
  </section>
}
