'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { API_BASE_URL } from '@/lib/constants'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'

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
      return 'bg-success'
    case 'degraded':
      return 'bg-warning'
    case 'error':
      return 'bg-error'
    default:
      return 'bg-neutral'
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'healthy':
      return 'Live'
    case 'degraded':
      return 'Degraded'
    case 'error':
      return 'Error'
    default:
      return 'Unknown'
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
      <div
        className="flex h-7 items-center gap-1.5 rounded-full border border-border px-2.5 text-xs text-muted-foreground"
        role="status"
      >
        <span className="size-1.5 animate-pulse rounded-full bg-neutral" />
        <span className="hidden sm:inline">Connecting…</span>
      </div>
    )
  }

  const { overall, sources } = data
  // Use the most recently successful source's timestamp
  const latestSuccess = [sources.yfinance, sources.akshare]
    .filter((s) => s.last_success_ago_seconds !== null)
    .sort(
      (a, b) =>
        (a.last_success_ago_seconds ?? Infinity) -
        (b.last_success_ago_seconds ?? Infinity)
    )[0]

  return (
    <div className="flex items-center gap-1">
      <Tooltip>
        <TooltipTrigger
          render={
            <div
              className="flex h-7 cursor-default items-center gap-1.5 rounded-full border border-border bg-card px-2.5 text-xs text-muted-foreground"
              role="status"
              aria-label={`Data source status: ${getStatusLabel(overall)}`}
            >
              <span
                className={cn('size-1.5 rounded-full', getStatusColor(overall))}
              />
              <span className="hidden sm:inline">{getStatusLabel(overall)}</span>
            </div>
          }
        />
        <TooltipContent side="bottom" className="space-y-1 text-xs">
          <p>
            Last update: {formatTimeAgo(latestSuccess?.last_success_ago_seconds ?? null)}
          </p>
          <p>
            yfinance: {sources.yfinance.status} · updated{' '}
            {formatTimeAgo(sources.yfinance.last_success_ago_seconds)}
          </p>
          <p>
            akshare: {sources.akshare.status} · updated{' '}
            {formatTimeAgo(sources.akshare.last_success_ago_seconds)}
          </p>
        </TooltipContent>
      </Tooltip>

      <button
        onClick={handleRefresh}
        disabled={isRefreshing}
        className="flex size-7 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
        title="Refresh all data"
        aria-label="Refresh all data"
      >
        <RefreshCw className={cn('size-3.5', isRefreshing && 'animate-spin')} />
      </button>
    </div>
  )
}
