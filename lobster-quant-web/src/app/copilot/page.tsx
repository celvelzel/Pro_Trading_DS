'use client'

import { FormEvent, useCallback, useState } from 'react'
import { Bot, Pause, Play, RefreshCw, Send, Square, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { PlanPanel } from '@/components/copilot/PlanPanel'
import { agentApi, AgentRequestError } from '@/lib/agent-api'
import { useAgentEvents } from '@/hooks/useAgentEvents'
import { useAgentRun } from '@/hooks/useAgentRun'

export default function CopilotPage() {
  const [goal, setGoal] = useState('分析 AAPL 的近期趋势、指标和风险，并给出有来源的研究摘要')
  const [runId, setRunId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [mode, setMode] = useState<'review' | 'auto'>('review')
  const [submitting, setSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const { run, setRun, loading, error, refresh } = useAgentRun(runId)
  const onGap = useCallback(() => { void refresh() }, [refresh])
  const { events } = useAgentEvents(runId, onGap)

  async function start(event: FormEvent) {
    event.preventDefault()
    if (!goal.trim()) return
    setSubmitting(true); setActionError(null)
    try {
      const conversation = conversationId ? { id: conversationId } : await agentApi.createConversation('研究 Copilot')
      setConversationId(conversation.id)
      const next = await agentApi.createRun(conversation.id, goal.trim(), mode)
      setRunId(next.id); setRun(next)
    } catch (cause) {
      setActionError(cause instanceof AgentRequestError ? cause.message : '无法创建 Agent run，请检查 API 服务')
    } finally { setSubmitting(false) }
  }

  async function action(name: 'approve' | 'pause' | 'cancel') {
    if (!run) return
    setActionError(null)
    try {
      const next = await agentApi[name](run.id, run.version)
      setRun(next)
    } catch (cause) {
      setActionError(cause instanceof AgentRequestError ? cause.message : '操作失败，请刷新后重试')
      void refresh()
    }
  }

  const displayError = actionError ?? error?.message
  return (
    <div className="min-h-full bg-background px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-col gap-4 border-b border-border/60 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-emerald-600"><Sparkles className="size-3.5" />Research Copilot</p>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">把研究问题变成可审计的执行轨迹</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">计划、工具摘要、异步回测和引用都会保留在 run 中。默认先审阅计划，再批准执行。</p>
          </div>
          <div className="rounded-full border border-border/60 bg-card px-3 py-1.5 text-xs text-muted-foreground">GET SSE · REST snapshot</div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card className="overflow-visible">
            <CardHeader><CardTitle className="flex items-center gap-2"><Bot className="size-5 text-primary" />新的研究任务</CardTitle></CardHeader>
            <CardContent>
              <form onSubmit={start} className="space-y-4">
                <label htmlFor="research-goal" className="text-sm font-medium">研究目标</label>
                <Input id="research-goal" value={goal} onChange={(event) => setGoal(event.target.value)} className="min-h-11" aria-describedby="goal-help" />
                <p id="goal-help" className="text-xs text-muted-foreground">不要输入 API key 或敏感信息；文档内容只作为不可信资料参与检索。</p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button type="submit" disabled={submitting || !goal.trim()} className="min-h-10 gap-2"><Send className="size-4" />{submitting ? '正在创建…' : '开始规划'}</Button>
                  <div className="flex rounded-lg border border-border p-1" role="group" aria-label="执行模式">
                    <button type="button" onClick={() => setMode('review')} className={`min-h-8 rounded-md px-3 text-xs transition-colors ${mode === 'review' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}>Review</button>
                    <button type="button" onClick={() => setMode('auto')} className={`min-h-8 rounded-md px-3 text-xs transition-colors ${mode === 'auto' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}>Auto</button>
                  </div>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card className="bg-slate-950 text-slate-50 ring-slate-800">
            <CardHeader><CardTitle className="flex items-center justify-between text-sm"><span>Run 状态</span>{loading && <RefreshCw className="size-4 animate-spin text-slate-400" />}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3"><span className="size-2.5 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,.7)]" /><span className="font-mono text-sm">{run?.status ?? 'idle'}</span></div>
              {run && <p className="font-mono text-xs text-slate-400">{run.id.slice(0, 8)} · v{run.version} · {events.length} events</p>}
              {run?.status === 'waiting_user' && <Button onClick={() => void action('approve')} className="min-h-10 w-full gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><Play className="size-4" />批准计划</Button>}
              {run && ['executing', 'waiting_tool', 'waiting_job'].includes(run.status) && <div className="flex gap-2"><Button variant="outline" onClick={() => void action('pause')} className="min-h-10 flex-1 border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800"><Pause className="size-4" />暂停</Button><Button variant="destructive" onClick={() => void action('cancel')} className="min-h-10 flex-1"><Square className="size-4" />取消</Button></div>}
              {run?.status === 'pause_requested' && <p className="text-xs text-amber-300">暂停会在当前原子步骤结束后生效。</p>}
              {displayError && <p role="alert" className="rounded-lg border border-red-400/30 bg-red-950/50 p-3 text-xs text-red-200">{displayError}</p>}
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
          <PlanPanel plan={run?.plan} />
          <Card><CardHeader><CardTitle className="text-sm">事件时间线</CardTitle></CardHeader><CardContent className="space-y-2"><div className="max-h-80 overflow-auto pr-1" aria-live="polite">{events.length === 0 ? <p className="text-sm text-muted-foreground">开始任务后，事件会按序显示。</p> : events.map((event) => <div key={event.event_id} className="flex gap-3 border-l border-border pl-3 text-xs"><span className="font-mono text-muted-foreground">{event.seq}</span><span>{event.event_type}</span></div>)}</div></CardContent></Card>
        </section>

        {run?.final_answer && <Card className="border-emerald-500/20"><CardHeader><CardTitle className="text-sm">最终回答</CardTitle></CardHeader><CardContent><p className="whitespace-pre-wrap text-sm leading-7">{run.final_answer}</p></CardContent></Card>}
      </div>
    </div>
  )
}
