import { API_BASE_URL } from './constants'
import type { AgentApiError, AgentMemoryItem, AgentRunSnapshot } from './agent-types'

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
    const body = await response.json().catch(() => ({})) as Partial<AgentApiError> & { detail?: string; error?: AgentApiError }
    const details = body.error ?? body
    throw new AgentRequestError(response.status, {
      code: details.code ?? `HTTP_${response.status}`,
      message: details.message ?? body.detail ?? 'Agent request failed',
      request_id: details.request_id,
      retryable: details.retryable,
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
  reject: (runId: string, expectedVersion: number, reason?: string) => request<AgentRunSnapshot>(`/runs/${runId}/reject`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion, reason }),
  }),
  clarify: (runId: string, expectedVersion: number, reason: string) => request<AgentRunSnapshot>(`/runs/${runId}/clarify`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion, reason }),
  }),
  resume: (runId: string, expectedVersion: number) => request<AgentRunSnapshot>(`/runs/${runId}/resume`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
  retry: (runId: string, expectedVersion: number) => request<AgentRunSnapshot>(`/runs/${runId}/retry`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
  pause: (runId: string, expectedVersion: number) => request<AgentRunSnapshot>(`/runs/${runId}/pause`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
  cancel: (runId: string, expectedVersion: number) => request<AgentRunSnapshot>(`/runs/${runId}/cancel`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
  listMemory: (conversationId: string) => request<AgentMemoryItem[]>(`/conversations/${conversationId}/memory`),
  createMemory: (conversationId: string, kind: AgentMemoryItem['kind'], content: string) => request<AgentMemoryItem>(`/conversations/${conversationId}/memory`, {
    method: 'POST', body: JSON.stringify({ kind, content }),
  }),
  deleteMemory: (memoryId: string, expectedVersion: number) => request<void>(`/memory/${memoryId}`, {
    method: 'DELETE', body: JSON.stringify({ expected_version: expectedVersion }),
  }),
  supersedeMemory: (memoryId: string, expectedVersion: number, content: string) => request<AgentMemoryItem>(`/memory/${memoryId}/supersede`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion, content }),
  }),
}

export function agentEventsUrl(runId: string, afterSeq: number) {
  return `${API_BASE_URL}/api/agent/runs/${runId}/events?after_seq=${afterSeq}&idle_seconds=30`
}
