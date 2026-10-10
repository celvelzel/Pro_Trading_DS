import type { ReactNode } from 'react'
import type { EvidenceRef, NumericFact, SourceProfile } from '@/types/financial-artifacts'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const labels: Record<string, string> = { verified: '事实已核验', partial: '部分结果 · 尚有缺失', insufficient_evidence: '证据不足 · 无法形成完整结论', feasible: '约束可行 · 研究建议', infeasible: '不可行 · 无满足约束的候选', insufficient_data: '数据不足 · 无法确认可行性', pass: '通过', fail: '未通过', unknown: '未知 · 尚未完成核验' }
export function Status({ value }: { value: string }) { return <Badge variant="outline">{labels[value] ?? value} ({value})</Badge> }
export function formatValue(value: number | null | undefined, unit = ''): string {
  if (value == null || !Number.isFinite(value)) return '未知'
  const displayValue = value === 0 ? 0 : unit === 'ratio' ? value * 100 : value
  // Four-decimal rounding must not erase finite nonzero facts in any unit.
  const rounded = new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(displayValue)
  const number = displayValue !== 0 && (rounded === '0' || rounded === '-0')
    ? new Intl.NumberFormat('en-US', { notation: 'scientific', maximumSignificantDigits: 4 }).format(displayValue)
    : rounded
  return unit === 'ratio' || unit === 'percent' || unit === 'percentage' ? `${number}%` : unit === 'percentage_points' ? `${number} 个百分点` : `${number}${unit ? ` ${unit}` : ''}`
}
export function formatFact(fact: NumericFact): string {
  if (fact.unit !== 'ratio') return formatValue(fact.value, fact.unit)
  return formatValue(fact.value, fact.name.includes('volume_ratio') ? '×' : 'ratio（原始比例）')
}
export function DataTable({ caption, headers, rows }: { caption: string; headers: string[]; rows: ReactNode[][] }) {
  return <Table><TableCaption>{caption}</TableCaption><TableHeader><TableRow>{headers.map(h => <TableHead scope="col" key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{rows.map((r, i) => <TableRow key={i}>{r.map((v, j) => j === 0 ? <TableHead scope="row" key={j}>{v}</TableHead> : <TableCell key={j} className="tabular-nums">{v}</TableCell>)}</TableRow>)}</TableBody></Table>
}
export function Details({ title, children }: { title: string; children: ReactNode }) { return <details className="rounded-lg border p-3"><summary className="cursor-pointer rounded-sm font-medium focus-visible:outline-2 focus-visible:outline-ring">{title}</summary><div className="mt-3 space-y-3 break-words text-sm">{children}</div></details> }
export function TextList({ values, empty = '无' }: { values: string[]; empty?: string }) { return values.length ? <ul className="list-disc space-y-1 pl-5">{values.map((v, i) => <li key={i}>{v}</li>)}</ul> : <p className="text-muted-foreground">{empty}</p> }
export function Source({ locator }: { locator: string }) {
  let safe = false
  try { const url = new URL(locator); safe = ['http:', 'https:'].includes(url.protocol) } catch { /* Local locators remain text. */ }
  return safe ? <a className="underline underline-offset-4" href={locator} target="_blank" rel="noopener noreferrer">{locator}</a> : <span>{locator}</span>
}
export function EvidenceDetails({ evidence, ids = [] }: { evidence: EvidenceRef[]; ids?: string[] }) {
  const missing = ids.filter(id => !evidence.some(e => e.id === id))
  return <Details title="来源与证据详情"><TextList values={missing.map(id => `未提供证据详情：${id}`)} empty={evidence.length ? '引用详情如下' : '暂无证据详情'} />{evidence.map(e => <div key={e.id} className="space-y-1 border-t pt-3"><p>{e.source_type} · {e.id}</p><Source locator={e.source_locator} /><p>发布时间：{e.published_at ?? '未知'} · 可用时间：{e.available_at ?? '未知'}</p><p>观测时间：{e.observed_at}</p><p>内容摘要：{e.excerpt ?? '未提供'}</p><p className="break-all text-muted-foreground">内容哈希：{e.content_hash}</p></div>)}</Details>
}
export function ResultShell({ title, sourceProfile = 'unknown', asOf, status, children }: { title: string; sourceProfile?: SourceProfile; asOf: string; status: string; children: ReactNode }) {
  return <Card><CardHeader><h2 className="text-base font-semibold">{title}</h2><Status value={status} /><p className="text-sm text-muted-foreground">数据截止：{asOf}</p><p className="text-sm">{sourceProfile === 'demo' ? '演示数据 · 不是你的持仓/行情' : sourceProfile === 'user' ? '用户提供的数据' : '来源类型未知 · 尚未确认数据归属'}</p></CardHeader><CardContent className="space-y-5">{children}</CardContent></Card>
}
export function PendingResult({ loading, error, title }: { loading?: boolean; error?: string | null; title: string }) { return <Card><CardContent><p role={error ? 'alert' : 'status'}>{title}：{loading ? '正在加载结果…' : error ? `加载失败：${error}` : '暂无结果'}</p></CardContent></Card> }
