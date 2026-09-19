import { CheckCircle2, CircleAlert, Clock3, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AgentEvent } from '@/lib/agent-types'

function eventIcon(eventType: string) {
  if (eventType.endsWith('completed') || eventType === 'run.resumed') return <CheckCircle2 className="size-4 text-emerald-500" aria-hidden="true" />
  if (eventType.endsWith('failed') || eventType === 'run.cancelled') return <CircleAlert className="size-4 text-red-500" aria-hidden="true" />
  if (eventType.includes('waiting') || eventType.includes('approval')) return <Clock3 className="size-4 text-amber-500" aria-hidden="true" />
  return <Loader2 className="size-4 text-primary" aria-hidden="true" />
}

export function Timeline({ events }: { events: AgentEvent[] }) {
  return (
    <Card>
      <CardHeader><CardTitle className="text-sm">执行时间线</CardTitle></CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">开始任务后，事件会按序显示。</p>
        ) : (
          <ol className="max-h-96 space-y-3 overflow-auto pr-1" aria-live="polite">
            {events.map((event) => (
              <li key={event.event_id} className="flex gap-3 border-l border-border pl-3 text-xs">
                <span className="mt-0.5">{eventIcon(event.event_type)}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{event.event_type}</span>
                    <span className="font-mono text-muted-foreground">#{event.seq}</span>
                  </div>
                  {typeof event.payload?.tool_name === 'string' && <p className="mt-1 text-muted-foreground">工具：{event.payload.tool_name}</p>}
                  {typeof event.payload?.job_id === 'string' && <p className="mt-1 text-muted-foreground">任务已交给 compute worker</p>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  )
}
