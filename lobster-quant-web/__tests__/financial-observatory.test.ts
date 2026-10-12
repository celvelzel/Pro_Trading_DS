import { describe, it, expect } from 'vitest'
import {
  categorizeEvent, deriveAgents, deriveBudget, derivePipeline, deriveTimeline,
  eventSafeSummary, parseRelations,
} from '@/lib/financial-observatory'
import type { AgentEvent } from '@/lib/agent-types'

const event = (seq: number, event_type: string, payload: Record<string, unknown>): AgentEvent =>
  ({ schema_version: 1, event_id: `e${seq}`, seq, event_type, timestamp: '', conversation_id: 'c', run_id: 'm', request_id: '', payload }) as AgentEvent

describe('financial observatory derivations', () => {
  it('categorizes persisted events into visual layers', () => {
    expect(categorizeEvent('mas.handoff', { phase: 'role:1' })).toBe('phase')
    expect(categorizeEvent('mas.invoked', { kind: 'model' })).toBe('specialist')
    expect(categorizeEvent('mas.invoked', { kind: 'tool' })).toBe('tool')
    expect(categorizeEvent('mas.budget_reserved', { counter: 'rounds' })).toBe('budget')
    expect(categorizeEvent('cross_mas.admitted', {})).toBe('cross')
    expect(categorizeEvent('mas.approve', {})).toBe('intervention')
    expect(categorizeEvent('mas.completed', {})).toBe('system')
    expect(deriveTimeline([event(1, 'mas.invoked', { kind: 'model' }), event(2, 'cross_mas.received', {})], 'cross')).toHaveLength(1)
  })
  it('keeps model prose and prompts out of every summary field', () => {
    expect(eventSafeSummary({ role: 'critic', action: 'challenge', summary: '机密分析', prompt: 'secret' }))
      .toBe('role: critic · action: challenge')
  })
  it('derives market pipeline stage progression from checkpoint phases', () => {
    const stages = derivePipeline([
      event(1, 'mas.handoff', { phase: 'initial_tool' }),
      event(2, 'mas.handoff', { phase: 'role:2' }),
      event(3, 'mas.challenge', { phase: 'critique:1:history' }),
    ], 'market_investigation')
    expect(stages.map(s => s.status)).toEqual(['done', 'done', 'active', 'pending'])
  })
  it('derives per-role activity, missing checks and budget from invocations', () => {
    const events = [
      event(1, 'mas.invoked', { role: 'critic', kind: 'model', invocation_key: 'critic:initial' }),
      event(2, 'mas.returned', { role: 'critic', kind: 'model', action: 'challenge', missing_checks: ['history'] }),
      event(3, 'mas.invoked', { role: 'price_volume', kind: 'tool', invocation_key: 'market:initial' }),
      event(4, 'mas.budget_reserved', { counter: 'rounds' }),
    ]
    const critic = deriveAgents(events, 'market_investigation').find(a => a.role === 'critic')!
    expect(critic.modelCalls).toBe(1)
    expect(critic.lastAction).toBe('challenge')
    expect(critic.missingChecks).toEqual(['history'])
    expect(deriveBudget(events)).toMatchObject({ modelCalls: 1, toolCalls: 1, rounds: 1, maxModelCalls: 16 })
  })
  it('parses only typed relations and never throws on unknown message types', () => {
    const parsed = parseRelations({ relations: [
      { relation_id: 'r1', relation_type: 'cross_admitted', source_run_id: 'm', target_run_id: 'p',
        envelope: { message_type: 'MARKET_EVIDENCE_READY', message_id: 'msg', causation_id: 'cause', deadline_at: 'd', created_at: 't', payload_ref: { artifact_id: 'a', schema_version: 1 } } },
      { relation_id: 'r2', relation_type: 'combined', source_run_id: 'm', target_run_id: 'p', envelope: {} },
      { relation_id: 'broken' },
    ] }, 'm')
    expect(parsed).toHaveLength(2)
    expect(parsed[0]).toMatchObject({ direction: 'out', messageType: 'MARKET_EVIDENCE_READY', payloadArtifactId: 'a', delivered: true })
    expect(parsed[1]).toMatchObject({ messageType: null, delivered: false })
    expect(() => parseRelations({ relations: 'nope' }, 'm')).toThrow()
  })
})
