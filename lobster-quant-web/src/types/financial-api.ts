import type { MarketArtifact, PortfolioArtifact } from './financial-artifacts'
export type WorkflowType = 'general' | 'market' | 'portfolio' | 'combined'
export type FinancialStatus = 'queued' | 'executing' | 'waiting_user' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'expired'
export interface FinancialRunBase {
  schema_version: 1; run_id: string; conversation_id: string; correlation_id: string
  status: FinancialStatus; mode: 'review' | 'auto'; version: number; error_code: string | null
  artifact_ref: { artifact_id: string; schema_version: 1 } | null
  limitations: string[]
}
export type FinancialRun = FinancialRunBase & (
  { mas_kind: 'market_investigation'; artifact: MarketArtifact | null; validation_outcome: 'verified' | 'partial' | 'insufficient_evidence' | 'pending' }
  | { mas_kind: 'portfolio_rebalance'; artifact: PortfolioArtifact | null; validation_outcome: 'feasible' | 'infeasible' | 'insufficient_data' | 'pending' })
export interface FinancialCreation {
  schema_version: 1; conversation_id: string; correlation_id: string
  market_run_id?: string | null; portfolio_run_id?: string | null
  runs: { run_id: string; mas_kind: FinancialRun['mas_kind']; status: FinancialStatus; version: number }[]
}
