'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  StockData,
  Indicators,
  Signal,
  OptionsAnalysis,
  RiskAssessment,
  ScanParams,
  ScanResponse,
  BacktestParams,
  BacktestResult,
} from '@/lib/types'

// ============================================================================
// Query Keys
// ============================================================================

export const stockKeys = {
  all: ['stocks'] as const,
  detail: (symbol: string) => [...stockKeys.all, symbol] as const,
  indicators: (symbol: string) => [...stockKeys.detail(symbol), 'indicators'] as const,
  signals: (symbol: string) => [...stockKeys.detail(symbol), 'signals'] as const,
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
// Stock Data Hooks
// ============================================================================

/**
 * Fetch stock data (OHLCV) for a given symbol.
 */
export function useStockData(symbol: string) {
  return useQuery<StockData>({
    queryKey: stockKeys.detail(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}`),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000, // 5 minutes
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
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Fetch trading signals for a given symbol.
 */
export function useStockSignals(symbol: string) {
  return useQuery<Signal>({
    queryKey: stockKeys.signals(symbol),
    queryFn: () => api.get(`/api/stocks/${symbol}/signals`),
    enabled: !!symbol,
    staleTime: 2 * 60 * 1000, // 2 minutes (signals change more frequently)
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
    staleTime: 5 * 60 * 1000,
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
    staleTime: 5 * 60 * 1000,
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
  })
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Prefetch stock data for faster navigation.
 */
export function usePrefetchStock() {
  const queryClient = useQueryClient()

  return (symbol: string) => {
    queryClient.prefetchQuery({
      queryKey: stockKeys.detail(symbol),
      queryFn: () => api.get(`/api/stocks/${symbol}`),
      staleTime: 5 * 60 * 1000,
    })
  }
}
