'use client'

import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL } from '@/lib/constants'

export interface KnowledgeDocument {
  id: string
  title: string
  document_type: string
  status: string
  current_version?: number | null
  failure_reason?: string | null
  content_hash: string
  embedding_model: string
  embedding_dimension: number
}

export function useDocuments() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents`)
      if (!response.ok) throw new Error('无法加载知识库')
      setDocuments(await response.json() as KnowledgeDocument[])
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法加载知识库')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  async function upload(file: File) {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${API_BASE_URL}/api/documents`, { method: 'POST', body: form })
    if (!response.ok) {
      const body = await response.json().catch(() => ({})) as { detail?: { message?: string } | string }
      throw new Error(typeof body.detail === 'string' ? body.detail : body.detail?.message ?? '上传失败')
    }
    await refresh()
  }

  async function remove(id: string) {
    const response = await fetch(`${API_BASE_URL}/api/documents/${id}`, { method: 'DELETE' })
    if (!response.ok) throw new Error('删除文档失败')
    await refresh()
  }

  return { documents, loading, error, refresh, upload, remove }
}
