import { CheckCircle2, Circle, Loader2, LockKeyhole } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AgentPlan, AgentStep } from '@/lib/agent-types'

const statusIcon = (step: AgentStep) => {
  if (step.status === 'succeeded') return <CheckCircle2 className="size-4 text-emerald-500" aria-hidden="true" />
  if (step.status === 'running') return <Loader2 className="size-4 animate-spin text-primary" aria-hidden="true" />
  return <Circle className="size-4 text-muted-foreground" aria-hidden="true" />
}

export function PlanPanel({ plan }: { plan: AgentPlan | null | undefined }) {
  if (!plan) return <div className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">计划生成后会显示在这里。</div>
  return (
    <Card className="border-primary/20 bg-card/80 shadow-sm">
      <CardHeader className="border-b border-border/60">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2"><span className="size-2 rounded-full bg-emerald-500" />执行计划</CardTitle>
          <span className="font-mono text-xs text-muted-foreground">Revision {plan.revision}</span>
        </div>
        <p className="text-sm leading-6 text-muted-foreground">{plan.goal}</p>
      </CardHeader>
      <CardContent className="space-y-3 pt-4">
        {plan.steps.map((step) => (
          <div key={step.id} className="flex items-start gap-3 rounded-lg border border-border/60 bg-background/50 p-3">
            <div className="mt-0.5">{statusIcon(step)}</div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                <span>{step.ordinal + 1}. {step.name}</span>
                {step.requires_confirmation && <span className="inline-flex items-center gap-1 text-xs text-amber-600"><LockKeyhole className="size-3" />需确认</span>}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{step.type}{step.tool_name ? ` · ${step.tool_name}` : ''}</p>
            </div>
            <span className="text-xs text-muted-foreground">{step.status}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
