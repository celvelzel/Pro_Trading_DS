'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useScannerHistory, useBacktestHistory } from '@/hooks/useHistory'
import { cn } from '@/lib/utils'
import { Search, FlaskConical, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

function ScanResultRow({ entry }: { entry: { id: string; timestamp: string; market: string; resultCount: number } }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/50 py-2 last:border-0">
      <div className="flex min-w-0 items-center gap-2.5">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent">
          <Search className="size-3.5 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{entry.market} Scan</p>
          <p className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
          </p>
        </div>
      </div>
      <span className="shrink-0 text-sm text-muted-foreground">
        <span className="font-mono font-medium tabular-nums text-foreground">{entry.resultCount}</span> stocks
      </span>
    </div>
  )
}

function BacktestResultRow({ entry }: { entry: { id: string; timestamp: string; symbol: string; strategyName?: string; metrics: { totalReturn: number; sharpeRatio: number } } }) {
  const isPositive = entry.metrics.totalReturn >= 0
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/50 py-2 last:border-0">
      <div className="flex min-w-0 items-center gap-2.5">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent">
          <FlaskConical className="size-3.5 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {entry.strategyName || 'Strategy'} · {entry.symbol}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className={cn('font-mono text-sm font-medium tabular-nums', isPositive ? 'text-success' : 'text-error')}>
          {isPositive ? '+' : ''}{entry.metrics.totalReturn.toFixed(1)}%
        </span>
        <span className="text-xs text-muted-foreground">
          SR: <span className="font-mono tabular-nums">{entry.metrics.sharpeRatio.toFixed(2)}</span>
        </span>
      </div>
    </div>
  )
}

export const RecentActivityCard = memo(function RecentActivityCard() {
  const { data: scanHistory, isLoading: scanLoading } = useScannerHistory()
  const { data: backtestHistory, isLoading: backtestLoading } = useBacktestHistory()

  const recentScans = scanHistory?.slice(0, 3) || []
  const recentBacktests = backtestHistory?.slice(0, 3) || []

  const isLoading = scanLoading || backtestLoading

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2.5">
                  <Skeleton className="size-7 rounded-md" />
                  <div className="space-y-1">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-16" />
                  </div>
                </div>
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (recentScans.length === 0 && recentBacktests.length === 0) {
    return (
      <Card className="transition-colors hover:border-primary/30">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
            <Clock className="mb-2 size-8 opacity-50" />
            <p className="text-sm">No recent activity</p>
            <p className="mt-1 text-xs">Run a scan or backtest to see results here</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="transition-colors hover:border-primary/30">
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {recentScans.length > 0 && (
          <div className="mb-4">
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Scans</h4>
            {recentScans.map((scan) => (
              <ScanResultRow key={scan.id} entry={scan} />
            ))}
          </div>
        )}
        {recentBacktests.length > 0 && (
          <div>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Backtests</h4>
            {recentBacktests.map((bt) => (
              <BacktestResultRow key={bt.id} entry={bt} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
})
