'use client'

import { useSearchParams } from 'next/navigation'
import { FinancialWorkflow } from '@/components/financial/FinancialWorkflow'
import type { WorkflowType } from '@/types/financial-api'
import { FormEvent, Suspense, useCallback, useState } from 'react'
import { Ban, Bot, Pause, Play, RefreshCw, RotateCcw, Send, Square, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { PlanPanel } from '@/components/copilot/PlanPanel'
import { MemoryPanel } from '@/components/copilot/MemoryPanel'
import { SourcesPanel } from '@/components/copilot/SourcesPanel'
import { Timeline } from '@/components/copilot/Timeline'
import { agentApi, AgentRequestError } from '@/lib/agent-api'
import { useAgentEvents } from '@/hooks/useAgentEvents'
import { useAgentRun } from '@/hooks/useAgentRun'

function GeneralCopilot() {
  const [goal, setGoal] = useState('分析 AAPL 的近期趋势、指标和风险，并给出有来源的研究摘要')
  const [runId, setRunId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [mode, setMode] = useState<'review' | 'auto'>('review')
  const [submitting, setSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [clarification, setClarification] = useState('')
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

  async function action(name: 'approve' | 'reject' | 'clarify' | 'pause' | 'resume' | 'cancel' | 'retry', reason?: string) {
    if (!run) return
    setActionError(null); setActionBusy(true)
    try {
      let next
      if (name === 'reject') next = await agentApi.reject(run.id, run.version, reason)
      else if (name === 'clarify') next = await agentApi.clarify(run.id, run.version, reason ?? '')
      else next = await agentApi[name](run.id, run.version)
      setRun(next); if (name === 'retry') setRunId(next.id)
    } catch (cause) {
      setActionError(cause instanceof AgentRequestError ? cause.message : '操作失败，请刷新后重试')
      void refresh()
    } finally { setActionBusy(false) }
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
              {run?.status === 'waiting_user' && <div className="space-y-3"><div className="flex gap-2"><Button disabled={actionBusy} onClick={() => void action('approve')} className="min-h-10 flex-1 gap-2 bg-emerald-500 text-slate-950 hover:bg-emerald-400"><Play className="size-4" />批准计划</Button><Button disabled={actionBusy} variant="outline" onClick={() => void action('reject', rejectReason)} className="min-h-10 gap-2 border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800"><Ban className="size-4" />重新规划</Button></div><label htmlFor="reject-reason" className="text-xs text-slate-400">给规划的反馈（可选）</label><Input id="reject-reason" value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} placeholder="例如：缩小数据范围，先完成风险分析" className="min-h-10 border-slate-700 bg-slate-900 text-slate-100 placeholder:text-slate-500" /><label htmlFor="clarification" className="text-xs text-slate-400">补充信息</label><Textarea id="clarification" value={clarification} onChange={(event) => setClarification(event.target.value)} placeholder="提供 Agent 继续规划所需的上下文" className="border-slate-700 bg-slate-900 text-slate-100 placeholder:text-slate-500" /><Button disabled={actionBusy || !clarification.trim()} variant="outline" onClick={() => void action('clarify', clarification.trim())} className="min-h-10 w-full border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800">提交补充信息</Button></div>}
              {run && ['executing', 'waiting_tool', 'waiting_job'].includes(run.status) && <div className="flex gap-2"><Button disabled={actionBusy} variant="outline" onClick={() => void action('pause')} className="min-h-10 flex-1 border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800"><Pause className="size-4" />暂停</Button><Button disabled={actionBusy} variant="destructive" onClick={() => void action('cancel')} className="min-h-10 flex-1"><Square className="size-4" />取消</Button></div>}
              {run?.status === 'paused' && <Button disabled={actionBusy} onClick={() => void action('resume')} className="min-h-10 w-full gap-2"><Play className="size-4" />恢复执行</Button>}
              {run?.status === 'failed' && <Button disabled={actionBusy} onClick={() => void action('retry')} className="min-h-10 w-full gap-2"><RotateCcw className="size-4" />创建重试任务</Button>}
              {run?.status === 'pause_requested' && <p className="text-xs text-amber-300">暂停会在当前原子步骤结束后生效。</p>}
              {displayError && <p role="alert" className="rounded-lg border border-red-400/30 bg-red-950/50 p-3 text-xs text-red-200">{displayError}</p>}
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
          <PlanPanel plan={run?.plan} />
          <Timeline events={events} />
        </section>

        {run?.final_answer && <Card className="border-emerald-500/20"><CardHeader><CardTitle className="text-sm">最终回答</CardTitle></CardHeader><CardContent><p className="whitespace-pre-wrap text-sm leading-7">{run.final_answer}</p></CardContent></Card>}
        <section className="grid gap-6 lg:grid-cols-2"><SourcesPanel citations={run?.citations ?? []} /><MemoryPanel conversationId={conversationId} /></section>
      </div>
    </div>
  )
}

function WorkflowCopilot() {
  const params = useSearchParams()
  const requested = params.get('workflow')
  const [workflowType, setWorkflowType] = useState<WorkflowType>(['market', 'portfolio', 'combined'].includes(requested ?? '') ? requested as WorkflowType : 'general')
  const [mode, setMode] = useState<'review' | 'auto'>('review')
  return <><nav className="flex flex-wrap items-center gap-3 border-b p-4" aria-label="研究工作流">
    <label>Workflow <select aria-label="Workflow" value={workflowType} onChange={e => setWorkflowType(e.target.value as WorkflowType)} className="ml-2 rounded border bg-background p-2">
      <option value="general">General</option><option value="market">Market</option><option value="portfolio">Portfolio</option><option value="combined">Combined</option>
    </select></label>
    {workflowType !== 'general' && <label>执行模式 <select aria-label="金融执行模式" value={mode} onChange={e => setMode(e.target.value as 'review' | 'auto')} className="ml-2 rounded border bg-background p-2"><option value="review">Review</option><option value="auto">Auto</option></select></label>}
  </nav>{workflowType === 'general' ? <GeneralCopilot /> : <main className="mx-auto max-w-6xl space-y-4 p-6"><h1 className="text-2xl font-semibold">Financial Research Copilot</h1><FinancialWorkflow key={workflowType} workflow={workflowType} mode={mode} symbol={params.get('symbol') ?? 'MU'} /></main>}</>
}
export default function CopilotPage() { return <Suspense fallback={<p role="status">正在加载工作流…</p>}><WorkflowCopilot /></Suspense> }
