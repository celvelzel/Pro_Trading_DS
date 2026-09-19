'use client'

import { useEffect, useReducer, useRef } from 'react'
import type { AgentEvent } from '@/lib/agent-types'
import { agentEventsUrl } from '@/lib/agent-api'

interface EventState {
  events: AgentEvent[]
  lastSeq: number
  gapDetected: boolean
}

type Action = { type: 'event'; event: AgentEvent } | { type: 'reset' }

export function agentEventReducer(state: EventState, action: Action): EventState {
  if (action.type === 'reset') return { events: [], lastSeq: 0, gapDetected: false }
  const event = action.event
  if (event.seq <= state.lastSeq) return state
  return {
    events: [...state.events, event],
    lastSeq: event.seq,
    gapDetected: state.gapDetected || event.seq > state.lastSeq + 1,
  }
}

const EVENT_TYPES = [
  'run.status_changed', 'plan.created', 'plan.approval_required', 'plan.approved', 'plan.rejected',
  'step.started', 'step.progress', 'step.completed', 'step.failed', 'tool.called', 'tool.completed',
  'tool.failed', 'citation.added', 'job.status_changed', 'user.input_required', 'run.completed',
  'run.failed', 'run.cancelled', 'run.pause_requested', 'run.paused', 'run.resumed', 'run.expired', 'memory.updated',
]

export function useAgentEvents(runId: string | null, onGap?: () => void) {
  const [{ events, lastSeq, gapDetected }, dispatch] = useReducer(agentEventReducer, { events: [], lastSeq: 0, gapDetected: false })

  const cursorRef = useRef(0)
  useEffect(() => {
    dispatch({ type: 'reset' })
    cursorRef.current = 0
    if (!runId) return
    let closed = false
    let source: EventSource | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let delay = 1000

    const connect = () => {
      if (closed) return
      source = new EventSource(agentEventsUrl(runId, cursorRef.current))
      const handle = (message: MessageEvent<string>) => {
        try {
          const next = JSON.parse(message.data) as AgentEvent
          cursorRef.current = Math.max(cursorRef.current, next.seq)
          dispatch({ type: 'event', event: next })
          delay = 1000
        } catch { /* malformed events are ignored */ }
      }
      EVENT_TYPES.forEach((type) => source?.addEventListener(type, handle))
      source.onerror = () => {
        source?.close()
        if (!closed) {
          reconnectTimer = setTimeout(connect, delay)
          delay = Math.min(delay * 2, 10000)
        }
      }
    }
    connect()
    return () => {
      closed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      source?.close()
    }
  }, [runId])

  useEffect(() => { if (gapDetected) onGap?.() }, [gapDetected, onGap])

  return { events, lastSeq, gapDetected }
}
