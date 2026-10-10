import type { EvidenceRef, PortfolioArtifact, ResultProps, RiskMetrics } from '@/types/financial-artifacts'
import { DataTable, Details, EvidenceDetails, formatValue, PendingResult, ResultShell, Status, TextList } from './result-shared'
export interface PortfolioResultProps extends ResultProps<PortfolioArtifact> { evidence?: EvidenceRef[] }
const riskLabels: [keyof Omit<RiskMetrics, 'tool_result_id'>, string][] = [['volatility', '年化波动率'], ['maximum_drawdown', '最大回撤'], ['concentration', '集中度'], ['cash_weight', '现金权重']]
export function PortfolioResult({ artifact, sourceProfile, loading, error, evidence = [] }: PortfolioResultProps) {
  if (loading || error || !artifact) return <PendingResult title="组合建议" loading={loading} error={error} />
  const symbols = [...new Set([...Object.keys(artifact.current_weights), ...Object.keys(artifact.proposed_weights)])]
  const risk = artifact.risk_comparison
  const sim = artifact.simulation
  return <ResultShell title="组合建议 / Portfolio" sourceProfile={sourceProfile} asOf={artifact.as_of} status={artifact.status}>
    <p className="break-all text-sm">持仓快照：{artifact.snapshot_id}</p><p className="text-sm text-muted-foreground">研究建议；不执行订单或修改持仓。</p>
    {symbols.length ? <DataTable caption="当前与建议权重（缺失值为未知）" headers={['资产', '当前', '建议']} rows={symbols.map(s => [s, formatValue(artifact.current_weights[s], 'ratio'), formatValue(artifact.proposed_weights[s], 'ratio')])} /> : <p>暂无权重数据。</p>}
    <section className="space-y-2"><h3 className="font-medium">约束核验</h3><Status value={artifact.constraint_check.status} /><TextList values={artifact.constraint_check.unknowns} empty="未列出未知项" />{artifact.constraint_check.violations.map((v, i) => <div key={i} className="rounded-lg border p-3"><p>{v.constraint}{v.symbol ? ` · ${v.symbol}` : ''}：{v.reason}</p><p className="text-sm text-muted-foreground">实际值：{formatValue(v.actual)} · 限值：{formatValue(v.limit)}（原始约束单位）</p></div>)}</section>
    <section><h3 className="mb-2 font-medium">风险对比</h3>{risk ? <DataTable caption="基于历史数据的风险指标；未知不等于零" headers={['指标', '调整前', '调整后']} rows={riskLabels.map(([key, label]) => [label, formatValue(risk.before[key], 'ratio'), formatValue(risk.after[key], 'ratio')])} /> : <p>数据不足，暂无风险对比。</p>}</section>
    <section className="space-y-2"><h3 className="font-medium">历史模拟 · 不是收益预测</h3>{sim ? <><p>净收益：{formatValue(sim.net_return, 'ratio')}</p><p className="text-sm">费用：{formatValue(sim.fees_bps, 'bps')} · 滑点：{formatValue(sim.slippage_bps, 'bps')}</p><p className="text-sm">再平衡频率：{sim.rebalance_cadence} · 价格调整：{sim.adjustment}</p><Details title="模拟假设"><TextList values={sim.assumptions} empty="未提供假设" /></Details></> : <p>暂无可用历史模拟。</p>}</section>
    <section><h3 className="mb-2 font-medium">限制与缺失</h3><TextList values={artifact.limitations} empty="未列出限制" /></section><EvidenceDetails evidence={evidence} ids={artifact.evidence_ids} />
    <Details title="运行与工具审计"><p>生成运行：{artifact.producing_run_id}</p><p>契约版本：{artifact.schema_version}</p><p>调整前风险工具：{risk?.before.tool_result_id ?? '未知'}</p><p>调整后风险工具：{risk?.after.tool_result_id ?? '未知'}</p><p>模拟工具：{sim?.tool_result_id ?? '未知'}</p></Details>
  </ResultShell>
}
