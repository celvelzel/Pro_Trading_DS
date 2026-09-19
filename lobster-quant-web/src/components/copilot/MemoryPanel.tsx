'use client'

import { useCallback, useEffect, useState } from 'react'
import { Brain, Check, Loader2, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { agentApi } from '@/lib/agent-api'
import type { AgentMemoryItem } from '@/lib/agent-types'

const kinds: Array<{ value: AgentMemoryItem['kind']; label: string }> = [
  { value: 'user_preference', label: '用户偏好' },
  { value: 'research_constraint', label: '研究约束' },
  { value: 'confirmed_fact', label: '已确认事实' },
]

export function MemoryPanel({ conversationId }: { conversationId: string | null }) {
  const [items, setItems] = useState<AgentMemoryItem[]>([])
  const [content, setContent] = useState('')
  const [kind, setKind] = useState<AgentMemoryItem['kind']>('research_constraint')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!conversationId) { setItems([]); return }
    setLoading(true)
    try { setItems(await agentApi.listMemory(conversationId)); setError(null) }
    catch (cause) { setError(cause instanceof Error ? cause.message : '无法读取记忆') }
    finally { setLoading(false) }
  }, [conversationId])

  useEffect(() => { void refresh() }, [refresh])

  async function addMemory() {
    if (!conversationId || !content.trim()) return
    setLoading(true); setError(null)
    try { await agentApi.createMemory(conversationId, kind, content.trim()); setContent(''); await refresh() }
    catch (cause) { setError(cause instanceof Error ? cause.message : '无法保存记忆') }
    finally { setLoading(false) }
  }

  async function remove(item: AgentMemoryItem) {
    setLoading(true); setError(null)
    try { await agentApi.deleteMemory(item.id, item.version); await refresh() }
    catch (cause) { setError(cause instanceof Error ? `${cause.message}，请刷新后重试` : '删除失败，请刷新后重试') }
    finally { setLoading(false) }
  }

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><Brain className="size-4 text-primary" />显式记忆</CardTitle><p className="text-xs leading-5 text-muted-foreground">只有你明确保存的偏好、约束和事实会进入后续上下文。</p></CardHeader>
      <CardContent className="space-y-4">
        {!conversationId ? <p className="text-sm text-muted-foreground">创建会话后可管理研究记忆。</p> : <>
          <div className="grid gap-2 sm:grid-cols-[150px_1fr_auto]">
            <label className="sr-only" htmlFor="memory-kind">记忆类型</label>
            <select id="memory-kind" value={kind} onChange={(event) => setKind(event.target.value as AgentMemoryItem['kind'])} className="h-10 rounded-lg border border-input bg-background px-3 text-sm">
              {kinds.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
            <label className="sr-only" htmlFor="memory-content">记忆内容</label>
            <Input id="memory-content" value={content} onChange={(event) => setContent(event.target.value)} placeholder="例如：研究默认使用日线数据" className="min-h-10" />
            <Button type="button" onClick={() => void addMemory()} disabled={loading || !content.trim()} className="min-h-10"><Check className="size-4" />保存</Button>
          </div>
          {loading && <p className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="size-3 animate-spin" />正在同步…</p>}
          {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
          {items.length === 0 ? <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">暂无显式记忆。</p> : <div className="space-y-2">{items.map((item) => <div key={item.id} className="flex items-start gap-3 rounded-lg border border-border/60 p-3"><div className="min-w-0 flex-1"><p className="text-sm leading-6">{item.content}</p><p className="mt-1 text-[10px] text-muted-foreground">{kinds.find((option) => option.value === item.kind)?.label} · v{item.version}</p></div><Button type="button" variant="ghost" size="icon" className="min-h-10 min-w-10" aria-label={`删除记忆 ${item.content}`} onClick={() => void remove(item)}><Trash2 className="size-4 text-muted-foreground" /></Button></div>)}</div>}
        </>}
      </CardContent>
    </Card>
  )
}
