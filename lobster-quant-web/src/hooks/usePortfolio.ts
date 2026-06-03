'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'

// ============================================================================
// Types
// ============================================================================

export interface Position {
  id: string
  symbol: string
  shares: number
  cost_basis: number
  opened_at: string
  updated_at: string
  strategy_id?: string
  current_price?: number
  market_value?: number
  pnl?: number
  pnl_percent?: number
}

export interface PositionDetail extends Position {
  current_price: number
  market_value: number
  cost_total: number
  pnl: number
  pnl_percent: number
}

export interface PortfolioSummary {
  positions: PositionDetail[]
  cash: number
  total_cost: number
  total_market_value: number
  total_pnl: number
  total_pnl_percent: number
  total_equity: number
  position_count: number
}

export interface PnlByStrategy {
  strategy_id: string
  position_count: number
  total_cost: number
  total_market_value: number
  pnl: number
  pnl_percent: number
}

export interface PortfolioPnl {
  strategies: PnlByStrategy[]
  total_pnl: number
  total_pnl_percent: number
}

export interface CashBalance {
  balance: number
  updated_at: string
}

export interface AddPositionRequest {
  symbol: string
  shares: number
  cost_basis: number
  strategy_id?: string
}

export interface UpdatePositionRequest {
  shares?: number
  cost_basis?: number
  strategy_id?: string
}

// ============================================================================
// Cache Timing Constants
// ============================================================================

const CACHE_TIMING = {
  /** Portfolio summary: 1min fresh, 5min gc (prices change frequently) */
  SUMMARY: { staleTime: 1 * 60 * 1000, gcTime: 5 * 60 * 1000 },
  /** P&L breakdown: 2min fresh, 10min gc */
  PNL: { staleTime: 2 * 60 * 1000, gcTime: 10 * 60 * 1000 },
  /** Cash balance: 5min fresh, 15min gc */
  CASH: { staleTime: 5 * 60 * 1000, gcTime: 15 * 60 * 1000 },
} as const

// ============================================================================
// Query Keys
// ============================================================================

export const portfolioKeys = {
  all: ['portfolio'] as const,
  summary: () => [...portfolioKeys.all, 'summary'] as const,
  pnl: () => [...portfolioKeys.all, 'pnl'] as const,
  cash: () => [...portfolioKeys.all, 'cash'] as const,
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Fetch full portfolio summary with P&L calculations.
 */
export function usePortfolioSummary() {
  return useQuery<PortfolioSummary>({
    queryKey: portfolioKeys.summary(),
    queryFn: () => api.get<PortfolioSummary>('/api/portfolio/'),
    ...CACHE_TIMING.SUMMARY,
  })
}

/**
 * Fetch P&L breakdown by strategy.
 */
export function usePortfolioPnl() {
  return useQuery<PortfolioPnl>({
    queryKey: portfolioKeys.pnl(),
    queryFn: () => api.get<PortfolioPnl>('/api/portfolio/pnl'),
    ...CACHE_TIMING.PNL,
  })
}

/**
 * Fetch current cash balance.
 */
export function useCashBalance() {
  return useQuery<CashBalance>({
    queryKey: portfolioKeys.cash(),
    queryFn: () => api.get<CashBalance>('/api/portfolio/cash'),
    ...CACHE_TIMING.CASH,
  })
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Add a new position to the portfolio.
 */
export function useAddPosition() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: AddPositionRequest) =>
      api.post<Position>('/api/portfolio/', request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all })
      toast.success('Position added')
    },
    onError: () => {
      toast.error('Failed to add position')
    },
  })
}

/**
 * Update an existing position.
 */
export function useUpdatePosition() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, ...request }: UpdatePositionRequest & { id: string }) =>
      api.put<Position>(`/api/portfolio/${id}`, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all })
      toast.success('Position updated')
    },
    onError: () => {
      toast.error('Failed to update position')
    },
  })
}

/**
 * Delete a position from the portfolio.
 */
export function useDeletePosition() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (positionId: string) =>
      api.delete<{ success: boolean }>(`/api/portfolio/${positionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all })
      toast.success('Position deleted')
    },
    onError: () => {
      toast.error('Failed to delete position')
    },
  })
}

/**
 * Set cash balance to a specific value.
 */
export function useSetCash() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (balance: number) =>
      api.put<CashBalance>('/api/portfolio/cash', { balance }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all })
      toast.success('Cash balance updated')
    },
    onError: () => {
      toast.error('Failed to update cash balance')
    },
  })
}

/**
 * Adjust cash balance (deposit/withdrawal).
 */
export function useAdjustCash() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (amount: number) =>
      api.post<CashBalance>('/api/portfolio/cash/adjust', { amount }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: portfolioKeys.all })
      toast.success('Cash balance adjusted')
    },
    onError: () => {
      toast.error('Failed to adjust cash balance')
    },
  })
}
