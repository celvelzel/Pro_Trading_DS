import { API_BASE_URL } from './constants'
import type { AgentApiError, AgentRunSnapshot } from './agent-types'

export class AgentRequestError extends Error {
  readonly details: AgentApiError
  readonly status: number

  constructor(status: number, details: AgentApiError) {
    super(details.message)
    this.name = 'AgentRequestError'
    this.status = status
    this.details = details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/agent${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as Partial<AgentApiError> & { detail?: string }
    throw new AgentRequestError(response.status, {
      code: body.code ?? `HTTP_${response.status}`,
      message: body.message ?? body.detail ?? 'Agent request failed',
      request_id: body.request_id,
      retryable: body.retryable,
    })
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const agentApi = {
  createConversation: (title?: string) => request<{ id: string; title?: string | null }>('/conversations', {
    method: 'POST', body: JSON.stringify({ title }),
  }),
  createRun: (conversationId: string, goal: string, mode: 'review' | 'auto' = 'review') => request<AgentRunSnapshot>('/runs', {
    method: 'POST', body: JSON.stringify({ conversation_id: conversationId, goal, mode }),
  }),
  getRun: (runId: string) => request<AgentRunSnapshot>(`/runs/${runId}`),
  approve: (runId: string, expectedVersion: number) => request<AgentRunSnapshot>(`/runs/${runId}/approve`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
  pause: (runId: string, expectedVersion: number) => request<AgentRunSnapshot>(`/runs/${runId}/pause`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
  cancel: (runId: string, expectedVersion: number) => request<AgentRunSnapshot>(`/runs/${runId}/cancel`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
}

export function agentEventsUrl(runId: string, afterSeq: number) {
  return `${API_BASE_URL}/api/agent/runs/${runId}/events?after_seq=${afterSeq}`
}
