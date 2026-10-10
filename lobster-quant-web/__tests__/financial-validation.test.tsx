import { describe, it, expect } from 'vitest'
import { parseFinancialCreation, parseFinancialRun } from '@/lib/financial-api'
import { eventSummary, PortfolioProvenance } from '@/components/financial/FinancialWorkflow'
import { render, screen } from '@testing-library/react'
import type { PortfolioArtifact } from '@/types/financial-artifacts'
const risk = { volatility: .1, maximum_drawdown: -.2, concentration: .4, cash_weight: .2, tool_result_id: 'before-exact' }
const artifact: PortfolioArtifact = { schema_version: 1, producing_run_id: 'p', snapshot_id: 'synthetic-mu-soxx-v1', as_of: '2026-09-29T20:05:00Z', current_weights: { MU: .5 }, proposed_weights: { MU: .25 }, constraint_check: { status: 'unknown', violations: [], unknowns: ['limited data'] }, risk_comparison: { before: risk, after: { ...risk, tool_result_id: 'after-exact' } }, simulation: { tool_result_id: 'sim-exact', adjustment: 'raw', rebalance_cadence: 'monthly', fees_bps: 1, slippage_bps: 2, net_return: null, assumptions: [] }, evidence_ids: ['unclassified-exact'], limitations: [], status: 'insufficient_data' }
const run = { schema_version: 1, run_id: 'p', conversation_id: 'c', correlation_id: 'pair', mas_kind: 'portfolio_rebalance', status: 'completed', mode: 'auto', version: 2, error_code: null, artifact_ref: { artifact_id: 'a', schema_version: 1 }, artifact, validation_outcome: 'insufficient_data', limitations: [] }
describe('untrusted financial response parsing', () => {
  it('accepts exact insufficient_data artifact', () => expect(parseFinancialRun(run, 'p', 'c', 'pair').validation_outcome).toBe('insufficient_data'))
  it.each([null, [], { ...run, run_id: 12 }, { ...run, correlation_id: '' }, { ...run, artifact_ref: null }, { ...run, artifact_ref: { artifact_id: '', schema_version: 1 } }, { ...run, artifact: { ...artifact, producing_run_id: 'other' } }, { ...run, artifact: { ...artifact, symbol: 'MU' } }, { ...run, artifact: { ...artifact, current_weights: null } }, { ...run, artifact: { ...artifact, proposed_weights: { MU: Infinity } } }, { ...run, artifact: { ...artifact, constraint_check: { status: 'pass', violations: [null], unknowns: [] } } }, { ...run, artifact: { ...artifact, risk_comparison: { before: null, after: risk } } }, { ...run, artifact: { ...artifact, simulation: { ...artifact.simulation, assumptions: null } } }, { ...run, artifact: { ...artifact, evidence_ids: [null] } }])('rejects malformed result %#', value => expect(() => parseFinancialRun(value)).toThrow())
  it('rejects wrong selected run/conversation/correlation', () => {
    expect(() => parseFinancialRun(run, 'm')).toThrow(); expect(() => parseFinancialRun(run, 'p', 'other')).toThrow(); expect(() => parseFinancialRun(run, 'p', 'c', 'other')).toThrow()
  })
  it.each([null, {}, { schema_version: 1, conversation_id: 'c', correlation_id: 'pair', portfolio_run_id: 'p', runs: [null] }, { schema_version: 1, conversation_id: 'c', correlation_id: 'pair', portfolio_run_id: 'wrong', runs: [{ run_id: 'p', mas_kind: 'portfolio_rebalance', status: 'queued', version: 1 }] }])('rejects malformed creation %#', value => expect(() => parseFinancialCreation(value, 'portfolio', 'c')).toThrow())
  it('shows exact persisted provenance without invented external citation', () => {
    render(<PortfolioProvenance artifact={artifact} />)
    for (const value of ['before-exact', 'after-exact', 'sim-exact', 'unclassified-exact', 'synthetic-mu-soxx-v1']) expect(screen.getByText(value)).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.getByText(/API 未暴露 provider URL/)).toBeInTheDocument()
  })
  it('explicitly shows SYSTEM_UNAVAILABLE and relation metadata without envelope reasoning', () => {
    expect(eventSummary({ relation_id: 'r', relation_type: 'cross_admitted', message_type: 'SYSTEM_UNAVAILABLE', reasoning: 'private' })).toBe('relation_id: r · relation_type: cross_admitted · message_type: SYSTEM_UNAVAILABLE')
  })
})

it('rejects malformed Market facts, hypotheses and source references', () => {
  const market = { ...run, run_id: 'm', mas_kind: 'market_investigation', validation_outcome: 'partial', artifact: { schema_version: 1, producing_run_id: 'm', symbol: 'MU', as_of: artifact.as_of, status: 'partial', limitations: [], numeric_facts: [], hypotheses: [], evidence: [] } }
  expect(parseFinancialRun(market).mas_kind).toBe('market_investigation')
  for (const bad of [ { numeric_facts: [null] }, { hypotheses: [{ explanation: 'x', support_ids: null, against_ids: [], disposition: 'supported' }] }, { evidence: [{ id: 'e', source_locator: null }] }, { limitations: [null] }, { as_of: 'invalid date' } ]) expect(() => parseFinancialRun({ ...market, artifact: { ...market.artifact, ...bad } })).toThrow()
})
