'use client'
import { useEffect, useState } from 'react'
import type { AgentEvent } from '@/lib/agent-types'
import { agentEventsUrl } from '@/lib/agent-api'
export const FINANCIAL_EVENTS = ['mas.coordination', 'mas.approval_recommendation', 'mas.revision_request', 'mas.verdict', 'mas.created', 'mas.retry_linked', 'mas.approve', 'mas.pause', 'mas.resume', 'mas.cancel', 'mas.expired', 'mas.review_required', 'mas.started', 'mas.checkpoint', 'mas.failure', 'mas.invoked', 'mas.returned', 'mas.invocation_failed', 'mas.budget_reserved', 'mas.artifact_created', 'mas.completed', 'mas.handoff', 'mas.challenge', 'mas.replan', 'cross_mas.admitted', 'cross_mas.received', 'cross_mas.linked']
export interface FinancialEventsState { events: AgentEvent[]; cursor: number }
export function acceptFinancialEvent(state: FinancialEventsState, event: AgentEvent, runId: string) {
  if (!event || !event.payload || typeof event.payload !== 'object' || Array.isArray(event.payload) || event.schema_version !== 1 || event.run_id !== runId || !Number.isInteger(event.seq) || !event.event_id || !FINANCIAL_EVENTS.includes(event.event_type)) return { state, gap: false }
  if (event.seq <= state.cursor || state.events.some(e => e.event_id === event.event_id)) return { state, gap: false }
  if (event.seq !== state.cursor + 1) return { state, gap: true }
  return { state: { events: [...state.events, event], cursor: event.seq }, gap: false }
}
export function useFinancialEvents(runId: string) {
  const [view, setView] = useState<FinancialEventsState>({ events: [], cursor: 0 })
  const [connection, setConnection] = useState('connecting')
  useEffect(() => {
    let state: FinancialEventsState = { events: [], cursor: 0 }
    let disposed = false
    let source: EventSource
    let timer: ReturnType<typeof setTimeout>
    let delay = 500
    const reconnect = () => {
      source.close()
      setConnection('reconnecting')
      clearTimeout(timer)
      timer = setTimeout(connect, delay)
      delay = Math.min(delay * 2, 10000)
    }
    const connect = () => {
      if (disposed) return
      source = new EventSource(agentEventsUrl(runId, state.cursor))
      source.onopen = () => { setConnection('connected'); delay = 500 }
      FINANCIAL_EVENTS.forEach(type => source.addEventListener(type, (message) => {
        try {
          const result = acceptFinancialEvent(state, JSON.parse((message as MessageEvent).data), runId)
          if (result.gap) { reconnect(); return }
          state = result.state
          setView(state)
        } catch { /* Ignore malformed transport messages; snapshot polling continues. */ }
      }))
      source.onerror = reconnect
    }
    connect()
    return () => { disposed = true; clearTimeout(timer); source.close() }
  }, [runId])
  return { ...view, connection }
}
