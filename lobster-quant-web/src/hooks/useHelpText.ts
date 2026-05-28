'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

// ============================================================================
// Types
// ============================================================================

export interface HelpText {
  key: string
  title?: string
  content: string
  updatedAt?: string
}

// ============================================================================
// Query Keys
// ============================================================================

export const helpKeys = {
  all: ['help'] as const,
  text: (key: string) => [...helpKeys.all, key] as const,
}

// ============================================================================
// Cache Timing
// ============================================================================

/**
 * Help text cache configuration.
 * Help content rarely changes → long staleTime
 */
const HELP_CACHE_TIMING = {
  staleTime: 60 * 60 * 1000, // 1 hour
  gcTime: 24 * 60 * 60 * 1000, // 24 hours
} as const

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch help text by key from the API.
 * Falls back to a default message if the API call fails.
 */
export function useHelpText(key: string) {
  return useQuery({
    queryKey: helpKeys.text(key),
    queryFn: async () => {
      try {
        const response = await api.get<HelpText>(`/api/help/${key}`)
        return response
      } catch {
        // Fallback: return a default help text if API fails
        return {
          key,
          content: 'Help content not available.',
        }
      }
    },
    ...HELP_CACHE_TIMING,
    // Don't refetch on window focus for help text
    refetchOnWindowFocus: false,
  })
}
