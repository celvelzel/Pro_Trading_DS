'use client'

import { useCallback, useEffect, useState } from 'react'
import type { AgentRunSnapshot } from '@/lib/agent-types'
import { agentApi, AgentRequestError } from '@/lib/agent-api'

export function useAgentRun(runId: string | null) {
  const [run, setRun] = useState<AgentRunSnapshot | null>(null)
  const [loading, setLoading] = useState(Boolean(runId))
  const [error, setError] = useState<AgentRequestError | null>(null)

  const refresh = useCallback(async () => {
    if (!runId) return null
    setLoading(true)
    try {
      const next = await agentApi.getRun(runId)
      setRun(next)
      setError(null)
      return next
    } catch (cause) {
      const nextError = cause instanceof AgentRequestError ? cause : new AgentRequestError(0, { code: 'NETWORK_ERROR', message: '无法连接 Agent 服务', retryable: true })
      setError(nextError)
      return null
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => { void refresh() }, [refresh])

  return { run, setRun, loading, error, refresh }
}
