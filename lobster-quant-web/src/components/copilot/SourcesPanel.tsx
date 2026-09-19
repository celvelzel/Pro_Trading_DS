import { ExternalLink, FileText, Gauge, Wrench } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AgentCitation } from '@/lib/agent-types'

function icon(type: AgentCitation['type']) {
  if (type === 'document') return <FileText className="size-4 text-primary" aria-hidden="true" />
  if (type === 'backtest_run') return <Gauge className="size-4 text-amber-600" aria-hidden="true" />
  return <Wrench className="size-4 text-emerald-600" aria-hidden="true" />
}

export function SourcesPanel({ citations }: { citations: AgentCitation[] }) {
  const unique = citations.filter((citation, index, all) => all.findIndex((item) => `${item.type}:${item.ref_id}` === `${citation.type}:${citation.ref_id}`) === index)
  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><ExternalLink className="size-4 text-primary" />来源与证据</CardTitle></CardHeader>
      <CardContent>
        {unique.length === 0 ? (
          <p className="text-sm text-muted-foreground">工具完成后，文档、工具结果和回测指标会显示在这里。</p>
        ) : (
          <div className="space-y-3">
            {unique.map((citation) => (
              <article key={`${citation.type}:${citation.ref_id}`} className="rounded-lg border border-border/60 bg-background/50 p-3">
                <div className="flex items-center gap-2 text-xs font-medium">{icon(citation.type)}<span>{citation.label}</span><span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">{citation.type}</span></div>
                {citation.excerpt && <p className="mt-2 line-clamp-4 text-xs leading-5 text-muted-foreground">{citation.excerpt}</p>}
                {citation.field_path && <p className="mt-2 font-mono text-[10px] text-muted-foreground">字段：{citation.field_path}</p>}
              </article>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
