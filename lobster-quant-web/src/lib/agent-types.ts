export type RunStatus =
  | 'created' | 'queued' | 'planning' | 'waiting_user' | 'executing'
  | 'waiting_tool' | 'waiting_job' | 'pause_requested' | 'paused'
  | 'cancelling' | 'completed' | 'failed' | 'cancelled' | 'expired'

export type StepStatus = 'pending' | 'running' | 'waiting_user' | 'succeeded' | 'failed' | 'skipped' | 'cancelled'

export interface AgentStep {
  id: string
  ordinal: number
  type: string
  name: string
  status: StepStatus
  tool_name?: string | null
  depends_on: string[]
  requires_confirmation: boolean
}

export interface AgentPlan {
  id: string
  revision: number
  goal: string
  assumptions: string[]
  completion_conditions: string[]
  steps: AgentStep[]
}

export interface AgentRunSnapshot {
  id: string
  conversation_id: string
  parent_run_id?: string | null
  status: RunStatus
  mode: 'review' | 'auto'
  goal: string
  version: number
  replan_count: number
  checkpoint: Record<string, unknown>
  final_answer?: string | null
  error_code?: string | null
  citations: AgentCitation[]
  plan?: AgentPlan | null
}

export interface AgentCitation {
  type: 'document' | 'tool_result' | 'backtest_run'
  ref_id: string
  label: string
  field_path?: string | null
  excerpt?: string | null
  metadata?: Record<string, unknown>
}

export interface AgentMemoryItem {
  id: string
  conversation_id: string
  kind: 'user_preference' | 'research_constraint' | 'confirmed_fact'
  content: string
  version: number
  source_message_id?: string | null
  superseded_by?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface AgentEvent {
  schema_version: number
  event_id: string
  seq: number
  event_type: string
  timestamp: string
  conversation_id: string
  run_id: string
  request_id: string
  payload: Record<string, unknown>
}

export interface AgentApiError {
  code: string
  message: string
  request_id?: string
  retryable?: boolean
  details?: Record<string, unknown>
}
