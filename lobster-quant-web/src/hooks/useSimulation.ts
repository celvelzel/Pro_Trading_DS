'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'

// ============================================================================
// Types
// ============================================================================

export interface SimulatedTrade {
  id: string
  symbol: string
  entryDate: string
  entryPrice: number
  exitDate?: string
  exitPrice?: number
  shares: number
  status: 'open' | 'closed'
  pnl?: number
  pnlPercent?: number
}

export interface PerformanceMetrics {
  strategyId: string
  window: string
  totalReturn: number
  volatility: number
  sharpeRatio: number
  maxDrawdown: number
  winRate: number
  totalTrades: number
}

export interface TradeJournalEntry {
  id: string
  strategyId: string
  symbol: string
  entryDate: string
  entryPrice: number
  exitDate?: string
  exitPrice?: number
  shares: number
  status: 'open' | 'closed'
  pnl?: number
  pnlPercent?: number
  entryScore?: number
  entrySignalType?: string
  entryReasons?: string[]
  exitReason?: string
  holdingDays?: number
}

export interface PerformanceChartPoint {
  date: string
  value: number
}

export interface PerformanceChartData {
  strategyId: string
  days: number
  strategyCurve: PerformanceChartPoint[]
  benchmarkCurve: PerformanceChartPoint[]
  benchmarkSymbol: string
  initialValue: number
  finalValue: number
  benchmarkFinalValue: number
}

// ============================================================================
// Cache Timing Constants
// ============================================================================

const CACHE_TIMING = {
  /** Simulation trades: 2min fresh, 10min gc */
  TRADES: { staleTime: 2 * 60 * 1000, gcTime: 10 * 60 * 1000 },
  /** Performance metrics: 5min fresh, 15min gc */
  PERFORMANCE: { staleTime: 5 * 60 * 1000, gcTime: 15 * 60 * 1000 },
  /** Trade journal: 2min fresh, 10min gc */
  JOURNAL: { staleTime: 2 * 60 * 1000, gcTime: 10 * 60 * 1000 },
  /** Performance chart: 5min fresh, 15min gc */
  CHART: { staleTime: 5 * 60 * 1000, gcTime: 15 * 60 * 1000 },
} as const

// ============================================================================
// Query Keys
// ============================================================================

export const simulationKeys = {
  all: ['simulation'] as const,
  trades: (strategyId: string) => [...simulationKeys.all, 'trades', strategyId] as const,
  performance: (strategyId: string, window: string) =>
    [...simulationKeys.all, 'performance', strategyId, window] as const,
  journal: (strategyId: string, days: number) =>
    [...simulationKeys.all, 'journal', strategyId, days] as const,
  chart: (strategyId: string, days: number) =>
    [...simulationKeys.all, 'chart', strategyId, days] as const,
}

// ============================================================================
// Simulation Data Hooks
// ============================================================================

/**
 * Fetch simulated trades for a given strategy.
 */
export function useSimulationTrades(strategyId: string) {
  return useQuery<SimulatedTrade[]>({
    queryKey: simulationKeys.trades(strategyId),
    queryFn: () => api.get(`/api/simulation/simulation/trades?strategy_id=${strategyId}`),
    enabled: !!strategyId,
    ...CACHE_TIMING.TRADES,
  })
}

/**
 * Fetch performance metrics for a given strategy and time window.
 */
export function useSimulationPerformance(strategyId: string, window: string = '1M') {
  return useQuery<PerformanceMetrics>({
    queryKey: simulationKeys.performance(strategyId, window),
    queryFn: () =>
      api.get(`/api/simulation/simulation/performance?strategy_id=${strategyId}&window=${window}`),
    enabled: !!strategyId,
    ...CACHE_TIMING.PERFORMANCE,
  })
}

/**
 * Fetch trade journal entries for a given strategy.
 */
export function useSimulationJournal(strategyId: string, days: number = 30) {
  return useQuery<TradeJournalEntry[]>({
    queryKey: simulationKeys.journal(strategyId, days),
    queryFn: () =>
      api.get(`/api/simulation/simulation/journal?strategy_id=${strategyId}&days=${days}`),
    enabled: !!strategyId,
    ...CACHE_TIMING.JOURNAL,
  })
}

/**
 * Fetch performance chart data (equity curve + benchmark) for a given strategy.
 */
export function useSimulationChart(strategyId: string, days: number = 30) {
  return useQuery<PerformanceChartData>({
    queryKey: simulationKeys.chart(strategyId, days),
    queryFn: () =>
      api.get(`/api/simulation/simulation/performance/chart?strategy_id=${strategyId}&days=${days}`),
    enabled: !!strategyId,
    ...CACHE_TIMING.CHART,
  })
}

// ============================================================================
// Simulation Mutation Hooks
// ============================================================================

interface RunSimulationParams {
  strategyId: string
  market: string
}

interface RunAllSimulationsParams {
  market: string
}

/**
 * Run a single strategy simulation.
 * Invalidates simulation queries on success to refresh data.
 */
export function useRunSimulation() {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, RunSimulationParams>({
    mutationFn: (params) =>
      api.post('/api/simulation/simulation/run', {
        strategyId: params.strategyId,
        market: params.market,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: simulationKeys.all })
      toast.success('Simulation completed')
    },
    onError: (error) => {
      toast.error(`Simulation failed: ${error.message}`)
    },
  })
}

/**
 * Run all strategy simulations for a market.
 * Invalidates simulation queries on success to refresh data.
 */
export function useRunAllSimulations() {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, RunAllSimulationsParams>({
    mutationFn: (params) =>
      api.post('/api/simulation/simulation/run-all', { market: params.market }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: simulationKeys.all })
      toast.success('All simulations completed')
    },
    onError: (error) => {
      toast.error(`Simulation failed: ${error.message}`)
    },
  })
}
