'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import type {
  AlertRule,
  AlertRulesResponse,
  TriggeredAlertsResponse,
  CreateAlertRuleRequest,
} from '@/lib/types'

// ============================================================================
// Cache Timing
// ============================================================================

const CACHE_TIMING = {
  /** Rules change infrequently */
  RULES: { staleTime: 30 * 1000, gcTime: 5 * 60 * 1000 },
  /** Triggered alerts poll every 60s */
  TRIGGERED: { staleTime: 55 * 1000, gcTime: 5 * 60 * 1000 },
} as const

// ============================================================================
// Query Keys
// ============================================================================

export const alertKeys = {
  all: ['alerts'] as const,
  rules: () => [...alertKeys.all, 'rules'] as const,
  triggered: () => [...alertKeys.all, 'triggered'] as const,
}

// ============================================================================
// Alert Rules Hooks
// ============================================================================

/**
 * Fetch all alert rules.
 */
export function useAlertRules() {
  return useQuery<AlertRulesResponse>({
    queryKey: alertKeys.rules(),
    queryFn: () => api.get('/api/alerts/rules'),
    ...CACHE_TIMING.RULES,
  })
}

/**
 * Create a new alert rule.
 */
export function useCreateAlertRule() {
  const queryClient = useQueryClient()

  return useMutation<AlertRule, Error, CreateAlertRuleRequest>({
    mutationFn: (params) => api.post('/api/alerts/rules', params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.rules() })
      toast.success('Alert rule created')
    },
    onError: (error) => {
      toast.error(`Failed to create alert: ${error.message}`)
    },
  })
}

/**
 * Delete an alert rule.
 */
export function useDeleteAlertRule() {
  const queryClient = useQueryClient()

  return useMutation<{ success: boolean }, Error, string>({
    mutationFn: (ruleId) => api.delete(`/api/alerts/rules/${ruleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.rules() })
      toast.success('Alert rule deleted')
    },
    onError: (error) => {
      toast.error(`Failed to delete alert: ${error.message}`)
    },
  })
}

/**
 * Toggle alert rule enabled/disabled.
 */
export function useToggleAlertRule() {
  const queryClient = useQueryClient()

  return useMutation<AlertRule, Error, { ruleId: string; enabled: boolean }>({
    mutationFn: ({ ruleId, enabled }) =>
      api.put(`/api/alerts/rules/${ruleId}`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.rules() })
    },
    onError: (error) => {
      toast.error(`Failed to update alert: ${error.message}`)
    },
  })
}

// ============================================================================
// Triggered Alerts Hooks
// ============================================================================

/**
 * Fetch triggered alerts (checks rules against current data).
 * Polls every 60 seconds when tab is active.
 */
export function useTriggeredAlerts() {
  return useQuery<TriggeredAlertsResponse>({
    queryKey: alertKeys.triggered(),
    queryFn: () => api.get('/api/alerts/triggered'),
    ...CACHE_TIMING.TRIGGERED,
    refetchInterval: 60 * 1000, // Poll every 60 seconds
    refetchIntervalInBackground: false, // Only when tab is active
  })
}

/**
 * Mark all triggered alerts as read.
 */
export function useMarkAlertsRead() {
  const queryClient = useQueryClient()

  return useMutation<{ success: boolean }, Error, void>({
    mutationFn: () => api.post('/api/alerts/read', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.triggered() })
    },
  })
}
