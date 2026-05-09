'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  AppSettings,
  SettingsUpdateRequest,
  SettingsResponse,
} from '@/lib/types'

// ============================================================================
// Cache Timing
// ============================================================================

const CACHE_TIMING = {
  /** Settings change infrequently → long staleTime */
  SETTINGS: { staleTime: 10 * 60 * 1000, gcTime: 30 * 60 * 1000 },
} as const

// ============================================================================
// Query Keys
// ============================================================================

export const settingsKeys = {
  all: ['settings'] as const,
  current: () => [...settingsKeys.all, 'current'] as const,
}

// ============================================================================
// Settings Hooks
// ============================================================================

/**
 * Fetch current application settings from the backend.
 */
export function useSettings() {
  return useQuery<SettingsResponse>({
    queryKey: settingsKeys.current(),
    queryFn: () => api.get('/api/settings'),
    ...CACHE_TIMING.SETTINGS,
  })
}

/**
 * Update application settings (partial update).
 * Invalidates the settings query on success.
 */
export function useUpdateSettings() {
  const queryClient = useQueryClient()

  return useMutation<SettingsResponse, Error, SettingsUpdateRequest>({
    mutationFn: (params) => api.put('/api/settings', params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}

/**
 * Reset all settings to backend defaults.
 * Invalidates the settings query on success.
 */
export function useResetSettings() {
  const queryClient = useQueryClient()

  return useMutation<SettingsResponse, Error, void>({
    mutationFn: () => api.post('/api/settings/reset', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}
