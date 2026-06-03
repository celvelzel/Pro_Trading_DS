'use client'

import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { API_BASE_URL } from '@/lib/constants'
import type {
  AlertRule,
  AlertRulesResponse,
  TriggeredAlertsResponse,
  TriggeredAlert,
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
 * @param disablePolling - Set to true when WebSocket is connected to avoid redundant polling.
 */
export function useTriggeredAlerts(disablePolling = false) {
  return useQuery<TriggeredAlertsResponse>({
    queryKey: alertKeys.triggered(),
    queryFn: () => api.get('/api/alerts/triggered'),
    ...CACHE_TIMING.TRIGGERED,
    refetchInterval: disablePolling ? false : 60 * 1000,
    refetchIntervalInBackground: false,
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

// ============================================================================
// WebSocket Real-Time Alerts
// ============================================================================

interface AlertWebSocketMessage {
  type: 'alert_triggered'
  alert: TriggeredAlert
}

/**
 * WebSocket hook for real-time alert push notifications.
 *
 * Connects to /ws/alerts on the backend. When an alert triggers,
 * the message is received instantly and the query cache is invalidated.
 * Automatically reconnects on disconnect with exponential backoff.
 *
 * @returns {{ connected: boolean }} Whether the WebSocket is currently connected.
 *
 * @example
 * ```tsx
 * const { connected } = useAlertWebSocket()
 * const { data } = useTriggeredAlerts(connected) // disables polling when WS is live
 * ```
 */
export function useAlertWebSocket() {
  const queryClient = useQueryClient()
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const attemptRef = useRef(0)

  useEffect(() => {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/ws/alerts'
    let unmounted = false

    function connect() {
      if (unmounted) return

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        attemptRef.current = 0 // reset backoff on successful connect
      }

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data: AlertWebSocketMessage = JSON.parse(event.data)
          if (data.type === 'alert_triggered' && data.alert) {
            // Push new alert into the React Query cache instantly
            queryClient.invalidateQueries({ queryKey: alertKeys.triggered() })
            toast.info(data.alert.message, { duration: 8000 })
          }
        } catch {
          // Ignore malformed messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        if (!unmounted) {
          // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
          const delay = Math.min(1000 * 2 ** attemptRef.current, 30_000)
          attemptRef.current += 1
          reconnectTimerRef.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = () => {
        // onerror triggers onclose, which handles reconnection
        ws.close()
      }
    }

    connect()

    return () => {
      unmounted = true
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [queryClient])

  return { connected }
}
