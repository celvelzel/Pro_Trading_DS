'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

// ============================================================================
// Types
// ============================================================================

export interface ScanHistoryEntry {
  id: string
  timestamp: string
  market: string
  minScore: number
  resultCount: number
  results: Array<{
    symbol: string
    name: string
    price: number
    change: number
    changePercent: number
    score: number
    signalType: 'bullish' | 'bearish' | 'neutral'
    probability: number
    reasons: string[]
  }>
}

export interface BacktestHistoryEntry {
  id: string
  timestamp: string
  symbol: string
  strategyId?: string
  strategyName?: string
  params: Record<string, unknown>
  metrics: {
    totalTrades: number
    winRate: number
    totalReturn: number
    maxDrawdown: number
    sharpeRatio: number
  }
  trades: Array<Record<string, unknown>>
  equityCurve: Array<Record<string, unknown>>
}

// ============================================================================
// Cache Timing
// ============================================================================

const CACHE_TIMING = {
  /** History data: 1min fresh, 5min gc */
  HISTORY: { staleTime: 1 * 60 * 1000, gcTime: 5 * 60 * 1000 },
} as const

// ============================================================================
// Query Keys
// ============================================================================

export const historyKeys = {
  all: ['history'] as const,
  scanner: () => [...historyKeys.all, 'scanner'] as const,
  backtest: () => [...historyKeys.all, 'backtest'] as const,
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch scanner history entries.
 * Returns the most recent scan results.
 */
export function useScannerHistory() {
  return useQuery<ScanHistoryEntry[]>({
    queryKey: historyKeys.scanner(),
    queryFn: () => api.get('/api/scanner/history'),
    ...CACHE_TIMING.HISTORY,
  })
}

/**
 * Fetch backtest history entries.
 * Returns the most recent backtest results.
 */
export function useBacktestHistory() {
  return useQuery<BacktestHistoryEntry[]>({
    queryKey: historyKeys.backtest(),
    queryFn: () => api.get('/api/backtest/history'),
    ...CACHE_TIMING.HISTORY,
  })
}
