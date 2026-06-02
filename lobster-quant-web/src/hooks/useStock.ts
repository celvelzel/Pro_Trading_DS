'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import type {
  StockData,
  Indicators,
  Signal,
  SignalHistoryEntry,
  OptionsAnalysis,
  RiskAssessment,
  ScanParams,
  ScanResponse,
  BacktestParams,
  BacktestResult,
  Candle,
} from '@/lib/types'

// ============================================================================
// Cache Timing Constants
// ============================================================================

/**
 * Financial data cache configuration.
 * - Price/OHLCV data changes frequently → shorter staleTime
 * - Signals change moderately → medium staleTime
 * - Indicators/Options/Risk are derived, change less → longer staleTime
 * - Scanner results are snapshots → short staleTime
 */
const CACHE_TIMING = {
  /** Real-time price data: 30s fresh, 5min gc */
  PRICE: { staleTime: 30 * 1000, gcTime: 5 * 60 * 1000 },
  /** Trading signals: 2min fresh, 10min gc */
  SIGNALS: { staleTime: 2 * 60 * 1000, gcTime: 10 * 60 * 1000 },
  /** Technical indicators: 5min fresh, 15min gc */
  INDICATORS: { staleTime: 5 * 60 * 1000, gcTime: 15 * 60 * 1000 },
  /** Options analysis: 5min fresh, 15min gc */
  OPTIONS: { staleTime: 5 * 60 * 1000, gcTime: 15 * 60 * 1000 },
  /** Risk assessment: 5min fresh, 15min gc */
  RISK: { staleTime: 5 * 60 * 1000, gcTime: 15 * 60 * 1000 },
  /** Scanner results: 1min fresh, 5min gc */
  SCANNER: { staleTime: 1 * 60 * 1000, gcTime: 5 * 60 * 1000 },
  /** Backtest results: 10min fresh, 30min gc (expensive to compute) */
  BACKTEST: { staleTime: 10 * 60 * 1000, gcTime: 30 * 60 * 1000 },
} as const

// ============================================================================
// Query Keys
// ============================================================================

export const stockKeys = {
  all: ['stocks'] as const,
  detail: (symbol: string) => [...stockKeys.all, symbol] as const,
  indicators: (symbol: string) => [...stockKeys.detail(symbol), 'indicators'] as const,
  signals: (symbol: string) => [...stockKeys.detail(symbol), 'signals'] as const,
  signalHistory: (symbol: string) => [...stockKeys.detail(symbol), 'signal-history'] as const,
  options: (symbol: string) => [...stockKeys.detail(symbol), 'options'] as const,
  risk: (symbol: string) => [...stockKeys.detail(symbol), 'risk'] as const,
}

export const scannerKeys = {
  all: ['scanner'] as const,
  scan: (params: ScanParams) => [...scannerKeys.all, params] as const,
}

export const backtestKeys = {
  all: ['backtest'] as const,
  run: (params: BacktestParams) => [...backtestKeys.all, params] as const,
}

// ============================================================================
// Select Transforms
// ============================================================================

/**
 * Extract only candle data for chart rendering.
 * Avoids re-renders when unrelated stock fields change.
 */
const selectCandles = (data: StockData) => data.candles

/**
 * Extract price summary (no candles array) for lightweight display.
 * Prevents re-renders when only candle data updates.
 */
const selectPriceSummary = (data: StockData) => ({
  symbol: data.symbol,
  name: data.name,
  price: data.price,
  change: data.change,
  changePercent: data.changePercent,
  volume: data.volume,
})

// ============================================================================
// Stock Data Hooks
// ============================================================================

/**
 * Fetch full stock data (OHLCV) for a given symbol.
 * Uses shorter staleTime since price data changes frequently.
 */
export function useStockData(symbol: string) {
  return useQuery<StockData>({
    queryKey: stockKeys.detail(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}`),
    enabled: !!symbol,
    ...CACHE_TIMING.PRICE,
  })
}

/**
 * Fetch only candle data for chart rendering.
 * Uses `select` to extract candles, preventing re-renders on unrelated changes.
 * Supports period parameter: 1d, 1w, 1m, 3m, 6m, ytd, 1y, 5y
 */
export function useStockCandles(symbol: string, period: string = 'ytd') {
  return useQuery<StockData, Error, Candle[]>({
    queryKey: [...stockKeys.detail(symbol), 'candles', period],
    queryFn: () => api.get(`/api/stocks/${symbol}?period=${period}`),
    enabled: !!symbol,
    select: selectCandles,
    ...CACHE_TIMING.PRICE,
  })
}

/**
 * Fetch only price summary (no candles) for lightweight display cards.
 * Uses `select` to strip the large candles array.
 */
export function useStockPriceSummary(symbol: string) {
  return useQuery<StockData, Error, ReturnType<typeof selectPriceSummary>>({
    queryKey: stockKeys.detail(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}`),
    enabled: !!symbol,
    select: selectPriceSummary,
    ...CACHE_TIMING.PRICE,
  })
}

/**
 * Fetch technical indicators for a given symbol.
 */
export function useStockIndicators(symbol: string) {
  return useQuery<Indicators>({
    queryKey: stockKeys.indicators(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}/indicators`),
    enabled: !!symbol,
    ...CACHE_TIMING.INDICATORS,
  })
}

/**
 * Fetch trading signals for a given symbol.
 * Signals change more frequently than indicators.
 */
export function useStockSignals(symbol: string) {
  return useQuery<Signal>({
    queryKey: stockKeys.signals(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}/signals`),
    enabled: !!symbol,
    ...CACHE_TIMING.SIGNALS,
  })
}

/**
 * Fetch signal history for a given symbol.
 * Returns an array of historical signal entries for charting.
 */
export function useStockSignalHistory(symbol: string) {
  return useQuery<SignalHistoryEntry[]>({
    queryKey: stockKeys.signalHistory(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}/signal-history`),
    enabled: !!symbol,
    ...CACHE_TIMING.SIGNALS,
  })
}

/**
 * Fetch options analysis for a given symbol.
 */
export function useStockOptions(symbol: string) {
  return useQuery<OptionsAnalysis>({
    queryKey: stockKeys.options(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}/options`),
    enabled: !!symbol,
    ...CACHE_TIMING.OPTIONS,
  })
}

/**
 * Fetch risk assessment for a given symbol.
 */
export function useStockRisk(symbol: string) {
  return useQuery<RiskAssessment>({
    queryKey: stockKeys.risk(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}/risk`),
    enabled: !!symbol,
    ...CACHE_TIMING.RISK,
  })
}

// ============================================================================
// Scanner Hooks
// ============================================================================

/**
 * Scan stocks based on market and minimum score.
 */
export function useScanStocks() {
  return useMutation<ScanResponse, Error, ScanParams>({
    mutationFn: (params) => api.post('/api/scanner/scan', params),
    onSuccess: (data) => {
      toast.success(`Found ${data.results?.length ?? 0} stocks`)
    },
    onError: (error) => {
      toast.error(`Scan failed: ${error.message}`)
    },
  })
}

// ============================================================================
// Backtest Hooks
// ============================================================================

/**
 * Run a strategy backtest.
 */
export function useRunBacktest() {
  return useMutation<BacktestResult, Error, BacktestParams>({
    mutationFn: (params) => api.post('/api/backtest/run', params),
    onSuccess: () => {
      toast.success('Backtest completed')
    },
    onError: (error) => {
      toast.error(`Backtest failed: ${error.message}`)
    },
  })
}

// ============================================================================
// Prefetch Hooks
// ============================================================================

/**
 * Prefetch all stock-related data for snappy navigation.
 * Call on hover/focus of stock links to warm the cache before navigation.
 *
 * Prefetches: stock data, indicators, signals, options, risk.
 * Each uses the same cache timing as the corresponding hook.
 */
export function usePrefetchStock() {
  const queryClient = useQueryClient()

  return (symbol: string) => {
    // Prefetch stock OHLCV data
    queryClient.prefetchQuery({
      queryKey: stockKeys.detail(symbol),
      queryFn: () => api.get(`/api/stocks/${symbol}`),
      ...CACHE_TIMING.PRICE,
    })

    // Prefetch indicators
    queryClient.prefetchQuery({
      queryKey: stockKeys.indicators(symbol),
      queryFn: () => api.get(`/api/stocks/${symbol}/indicators`),
      ...CACHE_TIMING.INDICATORS,
    })

    // Prefetch signals
    queryClient.prefetchQuery({
      queryKey: stockKeys.signals(symbol),
      queryFn: () => api.get(`/api/stocks/${symbol}/signals`),
      ...CACHE_TIMING.SIGNALS,
    })

    // Prefetch options
    queryClient.prefetchQuery({
      queryKey: stockKeys.options(symbol),
      queryFn: () => api.get(`/api/stocks/${symbol}/options`),
      ...CACHE_TIMING.OPTIONS,
    })

    // Prefetch risk
    queryClient.prefetchQuery({
      queryKey: stockKeys.risk(symbol),
      queryFn: () => api.get(`/api/stocks/${symbol}/risk`),
      ...CACHE_TIMING.RISK,
    })
  }
}
