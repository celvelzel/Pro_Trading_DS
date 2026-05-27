'use client'

import { useQueries } from '@tanstack/react-query'
import { useWatchlistStore } from '@/stores/watchlistStore'
import { api } from '@/lib/api'
import type { StockData, Signal } from '@/lib/types'

// ============================================================================
// Types
// ============================================================================

export interface WatchlistStockData {
  symbol: string
  price?: number
  change?: number
  changePercent?: number
  signal?: {
    type: 'bullish' | 'bearish' | 'neutral'
    score: number
  }
  isLoading: boolean
  error?: string
}

// ============================================================================
// Cache Timing
// ============================================================================

const CACHE_TIMING = {
  /** Price data: 30s fresh, 5min gc */
  PRICE: { staleTime: 30 * 1000, gcTime: 5 * 60 * 1000 },
  /** Signal data: 2min fresh, 10min gc */
  SIGNAL: { staleTime: 2 * 60 * 1000, gcTime: 10 * 60 * 1000 },
} as const

// ============================================================================
// Hook
// ============================================================================

/**
 * Fetches real-time data for all watchlist stocks.
 *
 * Uses TanStack Query's `useQueries` to fetch price and signal data
 * for each symbol in parallel. Results are merged into a single array
 * of `WatchlistStockData` objects.
 *
 * Features:
 * - Parallel fetching for all symbols
 * - Auto-refresh every 30 seconds for price data
 * - Per-stock loading and error states
 * - Graceful degradation if individual fetches fail
 *
 * @returns Object with `stocks` array, `isLoading` flag, and `refetch` function
 */
export function useWatchlistData() {
  const { symbols } = useWatchlistStore()

  // Fetch stock data for all symbols in parallel
  const stockQueries = useQueries({
    queries: symbols.map((symbol) => ({
      queryKey: ['stocks', symbol],
      queryFn: () => api.get<StockData>(`/api/stocks/${symbol}`),
      ...CACHE_TIMING.PRICE,
      retry: 2,
      refetchInterval: 30 * 1000, // Auto-refresh every 30s
      // Don't fetch if symbol is empty
      enabled: !!symbol,
    })),
  })

  // Fetch signal data for all symbols in parallel
  const signalQueries = useQueries({
    queries: symbols.map((symbol) => ({
      queryKey: ['stocks', symbol, 'signals'],
      queryFn: () => api.get<Signal>(`/api/stocks/${symbol}/signals`),
      ...CACHE_TIMING.SIGNAL,
      retry: 2,
      // Don't fetch if symbol is empty
      enabled: !!symbol,
    })),
  })

  // Merge data into unified format
  const stocks: WatchlistStockData[] = symbols.map((symbol, index) => {
    const stockQuery = stockQueries[index]
    const signalQuery = signalQueries[index]

    return {
      symbol,
      price: stockQuery.data?.price,
      change: stockQuery.data?.change,
      changePercent: stockQuery.data?.changePercent,
      signal: signalQuery.data
        ? {
            type: signalQuery.data.type,
            score: signalQuery.data.score,
          }
        : undefined,
      isLoading: stockQuery.isLoading || signalQuery.isLoading,
      error: stockQuery.error?.message || signalQuery.error?.message,
    }
  })

  // Aggregate loading state
  const isLoading =
    symbols.length > 0 &&
    (stockQueries.some((q) => q.isLoading) || signalQueries.some((q) => q.isLoading))

  // Check if any queries have errors
  const hasErrors = stockQueries.some((q) => q.isError) || signalQueries.some((q) => q.isError)

  // Refetch all data
  const refetch = () => {
    stockQueries.forEach((q) => q.refetch())
    signalQueries.forEach((q) => q.refetch())
  }

  return {
    stocks,
    isLoading,
    hasErrors,
    refetch,
  }
}
