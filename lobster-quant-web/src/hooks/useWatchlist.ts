'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

// ============================================================================
// Types
// ============================================================================

export interface WatchlistResponse {
  symbols: string[]
  groups: Record<string, string[]>
  tags: Record<string, string[]>
}

// ============================================================================
// Query Keys
// ============================================================================

export const watchlistKeys = {
  all: ['watchlist'] as const,
  detail: () => [...watchlistKeys.all, 'detail'] as const,
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch watchlist data from backend.
 */
export function useWatchlistQuery() {
  return useQuery<WatchlistResponse>({
    queryKey: watchlistKeys.detail(),
    queryFn: () => api.get('/api/watchlist/'),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Add a symbol to watchlist.
 */
export function useAddWatchlistSymbol() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (symbol: string) => 
      api.post('/api/watchlist/symbols', { symbol }),
    onSuccess: (data) => {
      queryClient.setQueryData(watchlistKeys.detail(), data)
    },
  })
}

/**
 * Remove a symbol from watchlist.
 */
export function useRemoveWatchlistSymbol() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (symbol: string) => 
      api.delete(`/api/watchlist/symbols/${symbol}`),
    onSuccess: (data) => {
      queryClient.setQueryData(watchlistKeys.detail(), data)
    },
  })
}

/**
 * Update watchlist groups.
 */
export function useUpdateWatchlistGroups() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (groups: Record<string, string[]>) => 
      api.put('/api/watchlist/groups', { groups }),
    onSuccess: (data) => {
      queryClient.setQueryData(watchlistKeys.detail(), data)
    },
  })
}

/**
 * Update watchlist tags.
 */
export function useUpdateWatchlistTags() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (tags: Record<string, string[]>) => 
      api.put('/api/watchlist/tags', { tags }),
    onSuccess: (data) => {
      queryClient.setQueryData(watchlistKeys.detail(), data)
    },
  })
}

/**
 * Clear entire watchlist.
 */
export function useClearWatchlist() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => api.delete('/api/watchlist/'),
    onSuccess: (data) => {
      queryClient.setQueryData(watchlistKeys.detail(), data)
    },
  })
}
