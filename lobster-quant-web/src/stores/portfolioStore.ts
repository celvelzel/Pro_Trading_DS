import { create } from 'zustand'
import { usePortfolioSummary, useAddPosition, useDeletePosition, useSetCash } from '@/hooks/usePortfolio'
import type { PositionDetail, PortfolioSummary } from '@/hooks/usePortfolio'

// ============================================================================
// Store Interface
// ============================================================================

interface PortfolioState {
  selectedPositionId: string | null
  addDialogOpen: boolean
  setSelectedPositionId: (id: string | null) => void
  setAddDialogOpen: (open: boolean) => void
}

// ============================================================================
// Store
// ============================================================================

export const usePortfolioStore = create<PortfolioState>()((set) => ({
  selectedPositionId: null,
  addDialogOpen: false,
  setSelectedPositionId: (id) => set({ selectedPositionId: id }),
  setAddDialogOpen: (open) => set({ addDialogOpen: open }),
}))

// ============================================================================
// Sync Hook
// ============================================================================

/**
 * Hook to sync portfolio store with backend API.
 * Provides portfolio data and mutation functions.
 */
export function useSyncPortfolio() {
  const { data: summary, isLoading, error, refetch } = usePortfolioSummary()
  const addMutation = useAddPosition()
  const deleteMutation = useDeletePosition()
  const setCashMutation = useSetCash()

  return {
    isLoading,
    error,
    summary: summary ?? null,
    positions: summary?.positions ?? [],
    cash: summary?.cash ?? 0,
    totalEquity: summary?.total_equity ?? 0,
    totalPnl: summary?.total_pnl ?? 0,
    totalPnlPercent: summary?.total_pnl_percent ?? 0,
    totalCost: summary?.total_cost ?? 0,
    totalMarketValue: summary?.total_market_value ?? 0,
    positionCount: summary?.position_count ?? 0,
    refetch,
    addPosition: (request: { symbol: string; shares: number; cost_basis: number; strategy_id?: string }) =>
      addMutation.mutate(request),
    deletePosition: (id: string) => deleteMutation.mutate(id),
    setCash: (balance: number) => setCashMutation.mutate(balance),
    isAdding: addMutation.isPending,
    isDeleting: deleteMutation.isPending,
  }
}
