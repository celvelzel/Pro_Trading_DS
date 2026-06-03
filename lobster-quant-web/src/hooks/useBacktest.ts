'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { showToastError } from '@/hooks/useApiQuery'
import type { BacktestMetrics } from '@/stores/strategyStore'

// ============================================================================
// Types
// ============================================================================

/** Backtest parameters matching BacktestForm component. */
export interface BacktestPageParams {
  mode: 'single' | 'portfolio'
  strategyId: string
  symbol?: string
  symbols?: string[]
  startDate?: string
  endDate?: string
}

interface BacktestTrade {
  entryDate: string
  exitDate?: string
  entryPrice: number
  exitPrice?: number
  returnPercent: number
  holdingDays: number
}

export interface BacktestPageResult {
  strategy_id: string
  strategy_name: string
  symbol?: string
  symbols?: string[]
  metrics: BacktestMetrics | null
  trades: BacktestTrade[]
  equityCurve: number[]
}

/** A saved backtest history entry from the API. */
export interface BacktestHistoryEntry {
  id: string
  timestamp: string
  symbol: string
  strategyId?: string
  strategyName?: string
  params: Record<string, unknown>
  metrics: Record<string, unknown>
  trades: Record<string, unknown>[]
  equityCurve: Record<string, unknown>[]
}

/** Single result from a parameter sweep. */
export interface SweepResultItem {
  paramValue: number
  metrics: Record<string, number>
}

/** Response from the sweep endpoint. */
export interface SweepResponse {
  parameterName: string
  symbol: string
  results: SweepResultItem[]
}

/** Parameters for the sweep mutation. */
export interface SweepParams {
  symbol: string
  strategyId?: string
  parameterName: 'holdingDays' | 'minScore'
  min: number
  max: number
  step: number
  holdingDays?: number
  minScore?: number
}

// ============================================================================
// Walk-Forward Types
// ============================================================================

/** Metrics for a single period (IS or OOS). */
export interface WindowMetrics {
  totalTrades: number
  winRate: number
  avgReturn: number
  cumulativeReturn: number
  maxDrawdown: number
  sharpeRatio: number
  sortinoRatio: number
  profitFactor: number
  bestTrade: number
  worstTrade: number
}

/** Results for a single walk-forward window. */
export interface WalkForwardWindow {
  windowIndex: number
  trainStart: string
  trainEnd: string
  testStart: string
  testEnd: string
  isMetrics: WindowMetrics
  oosMetrics: WindowMetrics
  degradation: number
}

/** Full walk-forward analysis result. */
export interface WalkForwardResult {
  symbol: string
  trainMonths: number
  testMonths: number
  stepMonths: number
  totalWindows: number
  windows: WalkForwardWindow[]
  avgIsSharpe: number
  avgOosSharpe: number
  avgDegradation: number
  avgOosWinRate: number
  avgOosReturn: number
  consistencyRatio: number
}

/** Parameters for the walk-forward mutation. */
export interface WalkForwardParams {
  symbol: string
  trainMonths?: number
  testMonths?: number
  stepMonths?: number
  holdingDays?: number
  minScore?: number
}

// ============================================================================
// Cache Timing Constants
// ============================================================================

const CACHE_TIMING = {
  /** Backtest results: 10min fresh, 30min gc (expensive to compute) */
  BACKTEST: { staleTime: 10 * 60 * 1000, gcTime: 30 * 60 * 1000 },
  /** History list: short stale, lightweight endpoint */
  HISTORY: { staleTime: 30 * 1000, gcTime: 5 * 60 * 1000 },
} as const

// ============================================================================
// Query Keys
// ============================================================================

export const backtestKeys = {
  all: ['backtest'] as const,
  run: (params: BacktestPageParams) => [...backtestKeys.all, params] as const,
  history: () => [...backtestKeys.all, 'history'] as const,
  sweep: (params: SweepParams) => [...backtestKeys.all, 'sweep', params] as const,
}

// ============================================================================
// Backtest Mutation Hooks
// ============================================================================

/**
 * Run a strategy backtest (single stock or portfolio).
 * Routes to the correct endpoint based on params.mode.
 * Caches results with 10min staleTime via queryClient.
 */
export function useRunBacktest() {
  const queryClient = useQueryClient()

  return useMutation<BacktestPageResult, Error, BacktestPageParams>({
    mutationFn: async (params) => {
      if (params.mode === 'single') {
        const queryParams = new URLSearchParams({
          strategy_id: params.strategyId,
          symbol: params.symbol || '',
        })
        if (params.startDate) queryParams.append('start_date', params.startDate)
        if (params.endDate) queryParams.append('end_date', params.endDate)

        return api.post(`/api/backtest/backtest/strategy?${queryParams}`, {})
      } else {
        return api.post('/api/backtest/backtest/portfolio', {
          symbols: params.symbols,
          strategy_id: params.strategyId,
          start_date: params.startDate,
          end_date: params.endDate,
        })
      }
    },
    onSuccess: (data, params) => {
      // Store result in query cache for potential reuse
      queryClient.setQueryData(backtestKeys.run(params), data)
      toast.success('Backtest completed')
    },
    onError: (error) => {
      showToastError(error)
    },
  })
}

// ============================================================================
// Backtest History Hooks
// ============================================================================

/**
 * Fetch saved backtest history entries.
 */
export function useBacktestHistory() {
  return useQuery<BacktestHistoryEntry[], Error>({
    queryKey: backtestKeys.history(),
    queryFn: () => api.get('/api/backtest/backtest/history'),
    ...CACHE_TIMING.HISTORY,
  })
}

/**
 * Delete a backtest history entry.
 */
export function useDeleteBacktestHistory() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (entryId) => api.delete(`/api/backtest/backtest/history/${entryId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: backtestKeys.history() })
      toast.success('Backtest deleted')
    },
    onError: (error) => {
      toast.error(`Delete failed: ${error.message}`)
    },
  })
}

// ============================================================================
// Parameter Sweep Hooks
// ============================================================================

/**
 * Run a parameter sweep backtest.
 */
export function useBacktestSweep() {
  return useMutation<SweepResponse, Error, SweepParams>({
    mutationFn: (params) => api.post('/api/backtest/backtest/sweep', params),
    onError: (error) => {
      toast.error(`Sweep failed: ${error.message}`)
    },
  })
}

// ============================================================================
// Walk-Forward Hooks
// ============================================================================

/**
 * Run walk-forward validation analysis.
 */
export function useWalkForward() {
  return useMutation<WalkForwardResult, Error, WalkForwardParams>({
    mutationFn: (params) => api.post('/api/backtest/backtest/walk-forward', params),
    onError: (error) => {
      toast.error(`Walk-forward failed: ${error.message}`)
    },
  })
}

export { CACHE_TIMING }
