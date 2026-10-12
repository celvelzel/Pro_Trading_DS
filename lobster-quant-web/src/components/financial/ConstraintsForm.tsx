'use client'
import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { financialApi } from '@/lib/financial-api'
import type { AllocationConstraints, ConstraintDraft } from '@/types/financial-api'

export function constraintErrors(value: AllocationConstraints, symbols: string[]) {
  const errors: string[] = []
  const nums = [value.min_cash_weight, value.max_equity_weight, ...Object.values(value.max_weight_by_symbol), ...Object.values(value.max_sector_weight)]
  if (nums.some(n => !Number.isFinite(n) || n < 0 || n > 1)) errors.push('比例必须在 0%–100% 之间。')
  if (value.min_cash_weight > (value.max_weight_by_symbol.CASH ?? 1)) errors.push('现金下限不能超过现金上限。')
  const unknown = Object.keys(value.max_weight_by_symbol).filter(s => !symbols.includes(s) && s !== 'CASH')
  if (unknown.length) errors.push(`标的不在当前快照中：${unknown.join(', ')}`)
  if (Object.keys(value.max_sector_weight).some(s => !s.trim())) errors.push('请填写行业名称。')
  return errors
}

interface Props {
  value: AllocationConstraints; symbols: string[]; sectors: string[]; disabled?: boolean
  onChange: (value: AllocationConstraints) => void; onPending: (pending: boolean) => void
}
export function ConstraintsForm({ value, symbols, sectors, disabled, onChange, onPending }: Props) {
  const [text, setText] = useState('')
  const [useLlm, setUseLlm] = useState(false)
  const [draft, setDraft] = useState<ConstraintDraft | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [symbol, setSymbol] = useState(symbols[0] ?? '')
  const [sector, setSector] = useState('')
  const [limit, setLimit] = useState('25')
  const [sectorLimit, setSectorLimit] = useState('30')
  const revision = useRef(0)
  const errorBox = useRef<HTMLDivElement>(null)
  function change(next: AllocationConstraints) { onChange(next) }
  async function parse() {
    const token = ++revision.current
    setBusy(true); setError(null); onPending(true)
    try {
      const result = await financialApi.parseConstraints({ text, symbols, sectors, use_llm: useLlm })
      if (token === revision.current) setDraft(result)
    } catch (e) {
      if (token === revision.current) { setError(e instanceof Error ? e.message : '解析失败'); errorBox.current?.focus() }
    } finally { if (token === revision.current) setBusy(false) }
  }
  function clearNatural() { revision.current++; setBusy(false); setText(''); setDraft(null); setError(null); onPending(false) }
  const issues = constraintErrors(value, symbols)
  return <fieldset disabled={disabled} className="space-y-5 rounded-xl border bg-card p-5" aria-label="组合约束">
    <legend className="px-2 font-semibold">组合约束</legend>
    <div className="space-y-3">
      <label htmlFor="constraint-language" className="block text-sm font-medium">用自然语言描述</label>
      <Textarea id="constraint-language" value={text} onChange={e => { revision.current++; setBusy(false); setText(e.target.value); setDraft(null); onPending(!!e.target.value.trim()); onChange({ ...value }) }} placeholder="例如：MU 不超过 25%，现金 20%–30%，股票总仓位最多 70%" />
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm"><input type="checkbox" checked={useLlm} onChange={e => { revision.current++; setBusy(false); setUseLlm(e.target.checked); setDraft(null); onPending(!!text.trim()); onChange({ ...value }) }} className="mr-2" />使用独立金融模型解析</label>
        <Button type="button" variant="outline" disabled={busy || !text.trim()} onClick={() => void parse()}>{busy ? '正在解析…' : '解析为约束草稿'}</Button>
        {text && <Button type="button" variant="ghost" onClick={clearNatural}>清除描述，手动填写</Button>}
      </div>
      <p className="text-xs text-muted-foreground">规则解析不需要模型；模型解析会发送这段描述及标的范围。两种方式均需核对确认。模糊偏好和未支持条件不会自动执行。</p>
      <div ref={errorBox} tabIndex={-1}>{error && <p role="alert" className="text-sm text-destructive">{error}</p>}</div>
      {draft && <div className="space-y-2 rounded-lg border bg-muted/30 p-4" aria-label="约束草稿">
        <p className="font-medium">解析结果 · 待核对</p>
        {draft.recognized.map((s, i) => <p key={i} className="text-sm">已识别：{s}</p>)}
        {draft.unresolved.map((s, i) => <p key={i} role="alert" className="text-sm text-destructive">待澄清：{s}</p>)}
        <p className="text-sm">现金至少 {Number((draft.constraints.min_cash_weight * 100).toFixed(2))}% · 现金最多 {Number(((draft.constraints.max_weight_by_symbol.CASH ?? 1) * 100).toFixed(2))}% · 股票总仓位最多 {Number((draft.constraints.max_equity_weight * 100).toFixed(2))}%</p>
        <ul className="text-sm">{Object.entries(draft.constraints.max_weight_by_symbol).filter(([s]) => s !== 'CASH').map(([s, cap]) => <li key={s}>{s} 最多 {Number((cap * 100).toFixed(2))}%</li>)}{Object.entries(draft.constraints.max_sector_weight).map(([s, cap]) => <li key={s}>{s} 行业最多 {Number((cap * 100).toFixed(2))}%</li>)}</ul>
        <details className="text-xs text-muted-foreground"><summary className="cursor-pointer">结构化约束（高级）</summary><pre className="mt-2 overflow-x-auto">{JSON.stringify(draft.constraints, null, 2)}</pre></details>
        <Button type="button" disabled={!!draft.unresolved.length || !!constraintErrors(draft.constraints, symbols).length} onClick={() => { change(draft.constraints); onPending(false) }}>将草稿填入表单</Button>
      </div>}
    </div>
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="space-y-2 text-sm">现金最低比例 (%)<Input type="number" min="0" max="100" step="0.1" value={Number.isFinite(value.min_cash_weight) ? value.min_cash_weight * 100 : ''} onChange={e => change({ ...value, min_cash_weight: e.target.value === '' ? 0 : Number(e.target.value) / 100 })} /></label>
      <label className="space-y-2 text-sm">现金最高比例 (%)<Input type="number" min="0" max="100" step="0.1" value={Number.isFinite(value.max_weight_by_symbol.CASH ?? 1) ? (value.max_weight_by_symbol.CASH ?? 1) * 100 : ''} onChange={e => change({ ...value, max_weight_by_symbol: { ...value.max_weight_by_symbol, CASH: e.target.value === '' ? 1 : Number(e.target.value) / 100 } })} /></label>
      <label className="space-y-2 text-sm">股票总仓位上限 (%)<Input type="number" min="0" max="100" step="0.1" value={Number.isFinite(value.max_equity_weight) ? value.max_equity_weight * 100 : ''} onChange={e => change({ ...value, max_equity_weight: e.target.value === '' ? 1 : Number(e.target.value) / 100 })} /></label>
    </div>
    <section className="space-y-3" aria-label="单资产上限">
      <h3 className="text-sm font-medium">单资产上限</h3>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">标的<select aria-label="约束标的" value={symbol} onChange={e => setSymbol(e.target.value)} className="ml-2 rounded-md border bg-background p-2">{symbols.map(s => <option key={s}>{s}</option>)}</select></label>
        <label className="text-sm">上限 (%)<Input aria-label="单资产上限比例" className="mt-1 w-28" type="number" min="0" max="100" value={limit} onChange={e => setLimit(e.target.value)} /></label>
        <Button type="button" variant="outline" disabled={!symbol || limit === '' || !Number.isFinite(Number(limit)) || Number(limit) < 0 || Number(limit) > 100} onClick={() => change({ ...value, max_weight_by_symbol: { ...value.max_weight_by_symbol, [symbol]: Number(limit) / 100 } })}>添加资产限制</Button>
      </div>
      <ul className="flex flex-wrap gap-2">{Object.entries(value.max_weight_by_symbol).filter(([s]) => s !== 'CASH').map(([s, cap]) => <li key={s} className="flex items-center gap-2 rounded-md border px-3 py-1 text-sm">{s} ≤ {Number((cap * 100).toFixed(2))}%<Button type="button" size="sm" variant="ghost" aria-label={`移除 ${s} 上限`} onClick={() => { const next = { ...value.max_weight_by_symbol }; delete next[s]; change({ ...value, max_weight_by_symbol: next }) }}>移除</Button></li>)}</ul>
    </section>
    <section className="space-y-3" aria-label="行业上限">
      <h3 className="text-sm font-medium">行业上限（需有可信分类）</h3>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">行业<Input className="mt-1 w-48" list="financial-sectors" value={sector} onChange={e => setSector(e.target.value)} placeholder="与数据分类标识一致" /></label>
        <datalist id="financial-sectors">{sectors.map(s => <option key={s} value={s} />)}</datalist>
        <label className="text-sm">上限 (%)<Input aria-label="行业上限比例" className="mt-1 w-28" type="number" min="0" max="100" value={sectorLimit} onChange={e => setSectorLimit(e.target.value)} /></label>
        <Button type="button" variant="outline" disabled={!sector.trim() || sectorLimit === '' || !Number.isFinite(Number(sectorLimit)) || Number(sectorLimit) < 0 || Number(sectorLimit) > 100} onClick={() => change({ ...value, max_sector_weight: { ...value.max_sector_weight, [sector.trim().toUpperCase()]: Number(sectorLimit) / 100 } })}>添加行业限制</Button>
      </div>
      <ul className="flex flex-wrap gap-2">{Object.entries(value.max_sector_weight).map(([s, cap]) => <li key={s} className="flex items-center gap-2 rounded-md border px-3 py-1 text-sm">{s} ≤ {Number((cap * 100).toFixed(2))}%<Button type="button" size="sm" variant="ghost" aria-label={`移除 ${s} 行业上限`} onClick={() => { const next = { ...value.max_sector_weight }; delete next[s]; change({ ...value, max_sector_weight: next }) }}>移除</Button></li>)}</ul>
    </section>
    <p className="text-xs text-muted-foreground">当前支持上述硬约束。最低股票仓位、预期收益、目标回撤等条件需额外实现；不会擅自换算。未设现金上限时，全现金仍可能是可行提案。</p>
    {issues.length > 0 && <div role="alert" className="rounded-md border border-destructive/40 p-3 text-sm text-destructive">{issues.map(s => <p key={s}>{s}</p>)}</div>}
  </fieldset>
}
