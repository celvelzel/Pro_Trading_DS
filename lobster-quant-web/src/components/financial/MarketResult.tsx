import type { MarketArtifact, ResultProps } from '@/types/financial-artifacts'
import { DataTable, Details, EvidenceDetails, formatFact, PendingResult, ResultShell, TextList } from './result-shared'
export function MarketResult({ artifact, sourceProfile, loading, error }: ResultProps<MarketArtifact>) {
  if (loading || error || !artifact) return <PendingResult title="行情调查" loading={loading} error={error} />
  return <ResultShell title={`${artifact.symbol} · 行情调查 / Market`} sourceProfile={sourceProfile} asOf={artifact.as_of} status={artifact.status}>
    <section><h3 className="mb-2 font-medium">Verified Facts / 已核验事实</h3><p className="text-sm text-muted-foreground">核验限于工具计算与证据出处，不代表来源真实性或因果关系已确认。</p>{artifact.numeric_facts.length ? <DataTable caption="已记录的数值事实（按原始单位展示）" headers={['指标', '数值']} rows={artifact.numeric_facts.map(f => [f.name, formatFact(f)])} /> : <p>暂无数值事实。</p>}</section>
    <section className="space-y-3"><h3 className="font-medium">Hypotheses / Potential Contributing Factors · 可能影响因素</h3><p className="text-sm text-muted-foreground">证据支持仅表示关联假设，不能确认因果关系。</p>{artifact.hypotheses.map((h, i) => <Details key={i} title={`${h.explanation} · ${{ supported: '有支持证据', contradicted: '有反证', unverified: '未核验' }[h.disposition]}`}><p>Supporting Evidence / 支持证据：{h.support_ids.join('、') || '无'}</p><p>Counter-evidence / 反证：{h.against_ids.join('、') || '无'}</p></Details>)}{!artifact.hypotheses.length && <p>暂无解释假设。</p>}</section>
    <section><h3 className="mb-2 font-medium">Limitations / Uncertainty · 限制与不确定性</h3><TextList values={artifact.limitations} empty="未列出限制" /></section>
    <EvidenceDetails evidence={artifact.evidence} ids={artifact.numeric_facts.map(f => f.evidence_id).concat(artifact.hypotheses.flatMap(h => [...h.support_ids, ...h.against_ids]))} />
    <Details title="运行与工具审计"><p>生成运行：{artifact.producing_run_id}</p><p>契约版本：{artifact.schema_version}</p><TextList values={artifact.numeric_facts.map(f => `${f.name} · 证据 ${f.evidence_id} · 工具 ${f.tool_result_id}`)} /></Details>
  </ResultShell>
}
