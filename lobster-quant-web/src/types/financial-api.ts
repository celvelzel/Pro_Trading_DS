import type { MarketArtifact, PortfolioArtifact } from './financial-artifacts'
export type WorkflowType = 'general' | 'market' | 'portfolio' | 'combined'
export type FinancialStatus = 'queued' | 'executing' | 'waiting_user' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'expired'
export interface FinancialRunBase {
  schema_version: 1; run_id: string; conversation_id: string; correlation_id: string
  status: FinancialStatus; mode: 'review' | 'auto'; version: number; error_code: string | null
  artifact_ref: { artifact_id: string; schema_version: 1 } | null
  limitations: string[]
  data_source?: 'demo' | 'user'
}

export interface AllocationConstraints {
  max_weight_by_symbol: Record<string, number>
  min_cash_weight: number
  max_equity_weight: number
  max_sector_weight: Record<string, number>
}
export interface ConstraintDraft {
  constraints: AllocationConstraints
  recognized: string[]
  unresolved: string[]
  parser: string
  requires_confirmation: boolean
}
export interface LivePrepared {
  dataset_id: string; conversation_id: string; as_of: string; snapshot_id: string | null
  symbols: string[]; sectors: string[]; cash: string | null; currency: string
  holdings: { symbol: string; quantity: string; price: string; price_at: string; source: string }[]
  limitations: string[]
}
export interface FinancialRequest {
  conversation_id: string; idempotency_key: string; mode: 'review' | 'auto'; dataset_id?: string
  market?: { symbol: string; as_of: string; sector_benchmark?: string }
  portfolio?: { portfolio_snapshot_id: string; as_of: string; user_constraints: AllocationConstraints }
}
export type FinancialRun = FinancialRunBase & (
  { mas_kind: 'market_investigation'; artifact: MarketArtifact | null; validation_outcome: 'verified' | 'partial' | 'insufficient_evidence' | 'pending' }
  | { mas_kind: 'portfolio_rebalance'; artifact: PortfolioArtifact | null; validation_outcome: 'feasible' | 'infeasible' | 'insufficient_data' | 'pending' })
export interface FinancialCreation {
  schema_version: 1; conversation_id: string; correlation_id: string
  market_run_id?: string | null; portfolio_run_id?: string | null
  runs: { run_id: string; mas_kind: FinancialRun['mas_kind']; status: FinancialStatus; version: number }[]
}
export type FinancialValidationOutcome = 'verified' | 'partial' | 'insufficient_evidence' | 'feasible' | 'infeasible' | 'insufficient_data' | 'pending'
export interface FinancialRunSummaryItem {
  schema_version: 1; run_id: string; mas_kind: FinancialRun['mas_kind']; status: FinancialStatus; version: number
  conversation_id: string; correlation_id: string; error_code: string | null
  validation_outcome: FinancialValidationOutcome
  as_of: string | null; created_at: string | null; updated_at: string | null
}
export interface FinancialRunHistory { schema_version: 1; runs: FinancialRunSummaryItem[] }
export interface FinancialRunFilters {
  conversationId?: string
  masKind?: FinancialRun['mas_kind']
  status?: FinancialStatus
}
