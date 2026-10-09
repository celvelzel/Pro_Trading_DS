import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { acceptFinancialEvent, FINANCIAL_EVENTS, useFinancialEvents } from '@/hooks/useFinancialEvents'
import { demoRequest, parseFinancialRun, financialApi } from '@/lib/financial-api'
import { eventSummary } from '@/components/financial/FinancialWorkflow'
const event = (seq: number, type = 'mas.created', run = 'm') => ({ schema_version: 1, event_id: `${run}-${seq}`, seq, event_type: type, timestamp: '', conversation_id: 'c', run_id: run, request_id: '', payload: {} })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })
describe('financial contracts', () => {
  it('accepts insufficient_data and rejects cross-kind status / wrong ownership', () => {
    const run = { schema_version: 1, mas_kind: 'portfolio_rebalance', run_id: 'p', conversation_id: 'c', correlation_id: 'pair', mode: 'auto', artifact_ref: null, version: 1, status: 'completed', validation_outcome: 'insufficient_data', artifact: null, limitations: [] }
    expect(parseFinancialRun(run).validation_outcome).toBe('insufficient_data')
    expect(() => parseFinancialRun({ ...run, validation_outcome: 'verified' })).toThrow()
    expect(() => parseFinancialRun({ ...run, artifact: { schema_version: 1, producing_run_id: 'other', status: 'insufficient_data' } })).toThrow()
  })
  it('creates only synthetic snapshot input and independent workflow scopes', () => {
    const p = demoRequest('portfolio', 'c', 'review', 'MU', 'k')
    expect(p).not.toHaveProperty('market')
    expect(p.portfolio).toEqual({ portfolio_snapshot_id: 'synthetic-mu-soxx-v1', as_of: '2026-09-29T20:05:00Z', user_constraints: { max_weight_by_symbol: { MU: .25 }, min_cash_weight: .2 } })
    expect(JSON.stringify(p)).not.toMatch(/cash_balance|positions|holdings/)
    expect(demoRequest('market', 'c', 'auto', 'AAPL', 'k')).not.toHaveProperty('portfolio')
  })
  it('rejects a combined response reusing one ID', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ schema_version: 1, runs: [{ run_id: 'm' }, { run_id: 'm' }] }) }))
    await expect(financialApi.create('combined', demoRequest('combined', 'c', 'auto', 'MU', 'k'))).rejects.toThrow()
  })
  it('renders only structured summaries and never prompt / reasoning', () => {
    expect(eventSummary({ role: 'analyst', evidence_ids: ['e1'], prompt: 'secret', reasoning: 'hidden', status: 'ready' })).toBe('role: analyst · status: ready · evidence_ids: e1')
  })
})
describe('financial SSE', () => {
  it.each(FINANCIAL_EVENTS)('recognizes %s', type => {
    expect(acceptFinancialEvent({ events: [], cursor: 0 }, event(1, type), 'm').state.cursor).toBe(1)
  })
  it('holds contiguous cursor on gap, ignores duplicates and foreign run', () => {
    const state = acceptFinancialEvent({ events: [], cursor: 0 }, event(1), 'm').state
    expect(acceptFinancialEvent(state, event(3), 'm')).toEqual({ state, gap: true })
    expect(acceptFinancialEvent(state, event(1), 'm').state).toBe(state)
    expect(acceptFinancialEvent(state, event(2, 'mas.created', 'p'), 'm').state).toBe(state)
  })
  it('keeps two real streams, replays gap and reconnects from independent contiguous cursors', () => {
    vi.useFakeTimers()
    class Source {
      static all: Source[] = []
      listeners: Record<string, (event: { data: string }) => void> = {}
      onerror?: () => void
      onopen?: () => void
      close = vi.fn()
      constructor(public url: string) { Source.all.push(this) }
      addEventListener(type: string, handler: (event: { data: string }) => void) { this.listeners[type] = handler }
      send(seq: number, run: string) { this.listeners['mas.created']({ data: JSON.stringify(event(seq, 'mas.created', run)) }) }
    }
    vi.stubGlobal('EventSource', Source)
    const { result, unmount } = renderHook(() => ({ market: useFinancialEvents('m'), portfolio: useFinancialEvents('p') }))
    act(() => { Source.all[0].send(1, 'm'); Source.all[1].send(1, 'p'); Source.all[1].send(2, 'p'); Source.all[0].send(3, 'm') })
    expect(result.current.market.cursor).toBe(1)
    expect(result.current.portfolio.cursor).toBe(2)
    act(() => vi.advanceTimersByTime(500))
    expect(Source.all[2].url).toContain('/m/events?after_seq=1')
    act(() => { Source.all[2].send(1, 'm'); Source.all[2].send(2, 'm'); Source.all[2].send(3, 'm'); Source.all[1].onerror?.() })
    expect(result.current.market.events).toHaveLength(3)
    act(() => vi.advanceTimersByTime(500))
    expect(Source.all[3].url).toContain('/p/events?after_seq=2')
    unmount()
    expect(Source.all[3].close).toHaveBeenCalled()
  })
})
