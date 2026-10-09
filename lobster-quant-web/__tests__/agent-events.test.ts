import { describe, expect, it } from 'vitest'
import { agentEventReducer } from '@/hooks/useAgentEvents'
import type { AgentEvent } from '@/lib/agent-types'

const event = (seq: number): AgentEvent => ({
  schema_version: 1,
  event_id: `event-${seq}`,
  seq,
  event_type: 'run.status_changed',
  timestamp: '2026-09-19T00:00:00Z',
  conversation_id: 'conversation',
  run_id: 'run',
  request_id: 'request',
  payload: { seq },
})

describe('agent event reducer', () => {
  it('deduplicates old and repeated events', () => {
    let state: ReturnType<typeof agentEventReducer> = { events: [], lastSeq: 0, gapDetected: false }
    state = agentEventReducer(state, { type: 'event', event: event(1) })
    state = agentEventReducer(state, { type: 'event', event: event(1) })
    expect(state.lastSeq).toBe(1)
    expect(state.events).toHaveLength(1)
  })

  it('marks a sequence gap so the REST snapshot can be refreshed', () => {
    let state: ReturnType<typeof agentEventReducer> = { events: [], lastSeq: 0, gapDetected: false }
    state = agentEventReducer(state, { type: 'event', event: event(1) })
    state = agentEventReducer(state, { type: 'event', event: event(3) })
    expect(state.gapDetected).toBe(true)
    expect(state.lastSeq).toBe(3)
  })
})
