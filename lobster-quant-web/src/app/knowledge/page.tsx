'use client'

import { ChangeEvent, useRef, useState } from 'react'
import { AlertCircle, CheckCircle2, Database, FileText, Loader2, Trash2, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useDocuments } from '@/hooks/useDocuments'

const statusLabel: Record<string, string> = {
  uploaded: '已上传', parsing: '解析中', chunking: '切片中', embedding: '向量化中', ready: '可检索', failed: '失败', deleted: '已删除',
}

export default function KnowledgePage() {
  const { documents, loading, error, refresh, upload, remove } = useDocuments()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true); setActionError(null)
    try { await upload(file) } catch (cause) { setActionError(cause instanceof Error ? cause.message : '上传失败') }
    finally { setUploading(false); event.target.value = '' }
  }

  return (
    <div className="min-h-full bg-background px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-col gap-4 border-b border-border/60 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div><p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-primary"><Database className="size-3.5" />Knowledge base</p><h1 className="text-2xl font-semibold tracking-tight">研究资料与可验证来源</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">支持 Markdown 和文本型 PDF。扫描 PDF 会明确失败，不会静默生成空知识库。</p></div>
          <input ref={inputRef} type="file" accept=".md,.markdown,.pdf" onChange={handleUpload} className="sr-only" aria-label="上传 Markdown 或 PDF 文档" />
          <Button onClick={() => inputRef.current?.click()} disabled={uploading} className="min-h-10 gap-2"><Upload className="size-4" />{uploading ? '正在处理…' : '上传文档'}</Button>
        </header>
        <div className="grid gap-4 sm:grid-cols-3"><Card><CardContent className="flex items-center gap-3 pt-4"><FileText className="size-5 text-muted-foreground" /><div><p className="text-2xl font-semibold">{documents.length}</p><p className="text-xs text-muted-foreground">文档</p></div></CardContent></Card><Card><CardContent className="flex items-center gap-3 pt-4"><CheckCircle2 className="size-5 text-emerald-500" /><div><p className="text-2xl font-semibold">{documents.filter((doc) => doc.status === 'ready').length}</p><p className="text-xs text-muted-foreground">可检索版本</p></div></CardContent></Card><Card><CardContent className="flex items-center gap-3 pt-4"><AlertCircle className="size-5 text-amber-500" /><div><p className="text-2xl font-semibold">10 MB</p><p className="text-xs text-muted-foreground">单文件限制 · 最多 200 页</p></div></CardContent></Card></div>
        {(error || actionError) && <div role="alert" className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-700"><AlertCircle className="size-4" />{error ?? actionError}<Button variant="link" size="sm" onClick={() => void refresh()}>重试</Button></div>}
        <Card><CardHeader><CardTitle className="text-base">文档状态</CardTitle></CardHeader><CardContent>{loading ? <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />正在读取知识库…</div> : documents.length === 0 ? <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">还没有资料。上传研究笔记或策略文档开始构建来源库。</div> : <div className="space-y-3">{documents.map((doc) => <div key={doc.id} className="flex flex-col gap-3 rounded-lg border border-border/60 p-4 sm:flex-row sm:items-center"><FileText className="size-5 text-muted-foreground" /><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{doc.title}</p><p className="mt-1 text-xs text-muted-foreground">{doc.document_type.toUpperCase()} · {doc.embedding_model} · v{doc.current_version ?? '—'}</p>{doc.failure_reason && <p className="mt-1 text-xs text-red-600">失败原因：{doc.failure_reason}</p>}</div><span className={`text-xs ${doc.status === 'ready' ? 'text-emerald-600' : doc.status === 'failed' ? 'text-red-600' : 'text-amber-600'}`}>{statusLabel[doc.status] ?? doc.status}</span><Button variant="ghost" size="icon" className="min-h-10 min-w-10" aria-label={`删除 ${doc.title}`} onClick={() => void remove(doc.id)}><Trash2 className="size-4" /></Button></div>)}</div>}</CardContent></Card>
      </div>
    </div>
  )
}
