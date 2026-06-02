'use client'

import { useMemo } from 'react'
import { useStockData, useStockRisk, useStockCandles } from '@/hooks/useStock'
import { useWatchlistData } from '@/hooks/useWatchlistData'

// ============================================================================
// Types
// ============================================================================

export interface DashboardDataState {
  /** Benchmark (SPY) stock data */
  benchmark: ReturnType<typeof useStockData>['data']
  /** Candle data for chart */
  candles: ReturnType<typeof useStockCandles>['data']
  /** Risk assessment data */
  risk: ReturnType<typeof useStockRisk>['data']
  /** Watchlist stocks data */
  watchlistStocks: ReturnType<typeof useWatchlistData>['stocks']
  /** Refetch watchlist function */
  refetchWatchlist: ReturnType<typeof useWatchlistData>['refetch']

  /** Loading states */
  isLoading: boolean
  isInitialLoad: boolean
  loadingProgress: number // 0-100

  /** Error states */
  hasError: boolean
  errors: {
    benchmark?: Error
    candles?: Error
    risk?: Error
  }
  /** Aggregated error message (first error found) */
  errorMessage: string | null

  /** Individual loading states for granular control */
  loadingStates: {
    benchmark: boolean
    candles: boolean
    risk: boolean
    watchlist: boolean
  }

  /** Timestamp of last successful data update */
  lastUpdated: number | null
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Centralized hook for all dashboard data.
 *
 * Fetches benchmark (SPY), candles, risk, and watchlist data in parallel
 * using React Query. Provides unified loading progress tracking and
 * error aggregation.
 *
 * Features:
 * - Parallel data fetching via React Query
 * - Loading progress (0-100) based on completed queries
 * - Unified error state with per-query error details
 * - Initial load detection for skeleton screen
 * - Last-updated timestamp for freshness indicator
 *
 * @param timeframe - Candle period (1d, 1w, 1m, 3m, 6m, 1y, 5y)
 */
export function useDashboardData(timeframe: string = '1y'): DashboardDataState {
  // All queries fire in parallel on mount
  const benchmarkQuery = useStockData('SPY')
  const candlesQuery = useStockCandles('SPY', timeframe)
  const riskQuery = useStockRisk('SPY')
  const { stocks: watchlistStocks, isLoading: watchlistLoading, refetch: refetchWatchlist } = useWatchlistData()

  // Compute aggregate states
  const state = useMemo(() => {
    const loadingStates = {
      benchmark: benchmarkQuery.isLoading,
      candles: candlesQuery.isLoading,
      risk: riskQuery.isLoading,
      watchlist: watchlistLoading,
    }

    const errors = {
      benchmark: benchmarkQuery.error ?? undefined,
      candles: candlesQuery.error ?? undefined,
      risk: riskQuery.error ?? undefined,
    }

    // Count completed queries (4 total)
    const queryStates = [
      !benchmarkQuery.isLoading,
      !candlesQuery.isLoading,
      !riskQuery.isLoading,
      !watchlistLoading,
    ]
    const completedCount = queryStates.filter(Boolean).length
    const loadingProgress = Math.round((completedCount / 4) * 100)

    // Initial load = all queries still loading (no data yet)
    const isInitialLoad = benchmarkQuery.isLoading && candlesQuery.isLoading && riskQuery.isLoading

    // Any query still loading
    const isLoading = benchmarkQuery.isLoading || candlesQuery.isLoading || riskQuery.isLoading || watchlistLoading

    // Error aggregation
    const hasError = !!(errors.benchmark || errors.candles || errors.risk)
    const errorMessage = errors.benchmark?.message || errors.candles?.message || errors.risk?.message || null

    // Last updated = most recent dataUpdatedAt across all queries
    const timestamps = [
      benchmarkQuery.dataUpdatedAt,
      candlesQuery.dataUpdatedAt,
      riskQuery.dataUpdatedAt,
    ].filter((t) => t > 0)
    const lastUpdated = timestamps.length > 0 ? Math.max(...timestamps) : null

    return {
      benchmark: benchmarkQuery.data,
      candles: candlesQuery.data,
      risk: riskQuery.data,
      watchlistStocks,
      refetchWatchlist,

      isLoading,
      isInitialLoad,
      loadingProgress,

      hasError,
      errors,
      errorMessage,

      loadingStates,
      lastUpdated,
    }
  }, [
    benchmarkQuery.data,
    benchmarkQuery.isLoading,
    benchmarkQuery.error,
    benchmarkQuery.dataUpdatedAt,
    candlesQuery.data,
    candlesQuery.isLoading,
    candlesQuery.error,
    candlesQuery.dataUpdatedAt,
    riskQuery.data,
    riskQuery.isLoading,
    riskQuery.error,
    riskQuery.dataUpdatedAt,
    watchlistStocks,
    watchlistLoading,
    refetchWatchlist,
  ])

  return state
}
