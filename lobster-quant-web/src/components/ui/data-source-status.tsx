'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { API_BASE_URL } from '@/lib/constants'
import { useState } from 'react'

interface DataSourceInfo {
  status: 'healthy' | 'degraded' | 'error' | 'unknown'
  last_success: string | null
  last_success_ago_seconds: number | null
  error_count_1h: number
}

interface HealthResponse {
  overall: 'healthy' | 'degraded' | 'error'
  sources: {
    yfinance: DataSourceInfo
    akshare: DataSourceInfo
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'healthy':
      return 'bg-green-500'
    case 'degraded':
      return 'bg-yellow-500'
    case 'error':
      return 'bg-red-500'
    default:
      return 'bg-gray-400'
  }
}

function formatTimeAgo(seconds: number | null): string {
  if (seconds === null) return 'Never'
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

export function DataSourceStatus() {
  const queryClient = useQueryClient()
  const [isRefreshing, setIsRefreshing] = useState(false)

  const { data, isLoading } = useQuery<HealthResponse>({
    queryKey: ['health', 'datasource'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/health/datasource`)
      if (!res.ok) throw new Error('Health check failed')
      return res.json()
    },
    refetchInterval: 30_000, // Poll every 30 seconds
    staleTime: 10_000,
  })

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await queryClient.invalidateQueries()
    // Brief delay so spinner is visible
    setTimeout(() => setIsRefreshing(false), 600)
  }

  if (isLoading || !data) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-text-tertiary">
        <span className="w-2 h-2 rounded-full bg-gray-300 animate-pulse" />
        <span>Loading status...</span>
      </div>
    )
  }

  const { overall, sources } = data
  // Use the most recently successful source's timestamp
  const latestSuccess = [sources.yfinance, sources.akshare]
    .filter((s) => s.last_success_ago_seconds !== null)
    .sort((a, b) => (a.last_success_ago_seconds ?? Infinity) - (b.last_success_ago_seconds ?? Infinity))[0]

  return (
    <div className="px-3 py-2 space-y-2">
      {/* Status indicator row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${getStatusColor(overall)}`} />
          <span className="text-xs text-text-secondary">
            Data: {overall === 'healthy' ? 'OK' : overall === 'degraded' ? 'Degraded' : overall === 'error' ? 'Error' : 'Unknown'}
          </span>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="p-1 rounded hover:bg-bg-hover transition-colors disabled:opacity-50"
          title="Refresh all data"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 text-text-tertiary ${isRefreshing ? 'animate-spin' : ''}`}
          />
        </button>
      </div>

      {/* Last updated text */}
      <div className="text-[11px] text-text-tertiary">
        Updated: {formatTimeAgo(latestSuccess?.last_success_ago_seconds ?? null)}
      </div>
    </div>
  )
}
