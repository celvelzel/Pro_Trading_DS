'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useScannerHistory, useBacktestHistory } from '@/hooks/useHistory'
import { cn } from '@/lib/utils'
import { Search, FlaskConical, Clock, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

function ScanResultRow({ entry }: { entry: { id: string; timestamp: string; market: string; resultCount: number } }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-2">
        <Search className="w-4 h-4 text-primary" />
        <div>
          <p className="text-sm font-medium text-text-primary">{entry.market} Scan</p>
          <p className="text-xs text-text-secondary">
            {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
          </p>
        </div>
      </div>
      <span className="text-sm font-medium text-text-primary">{entry.resultCount} stocks</span>
    </div>
  )
}

function BacktestResultRow({ entry }: { entry: { id: string; timestamp: string; symbol: string; strategyName?: string; metrics: { totalReturn: number; sharpeRatio: number } } }) {
  const isPositive = entry.metrics.totalReturn >= 0
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-2">
        <FlaskConical className="w-4 h-4 text-primary" />
        <div>
          <p className="text-sm font-medium text-text-primary">
            {entry.strategyName || 'Strategy'} · {entry.symbol}
          </p>
          <p className="text-xs text-text-secondary">
            {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={cn('text-sm font-medium', isPositive ? 'text-success' : 'text-error')}>
          {isPositive ? '+' : ''}{entry.metrics.totalReturn.toFixed(1)}%
        </span>
        <span className="text-xs text-text-secondary">SR: {entry.metrics.sharpeRatio.toFixed(2)}</span>
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
      <Card className="animate-pulse">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 bg-gray-200 rounded" />
                  <div className="space-y-1">
                    <div className="h-4 bg-gray-200 rounded w-24" />
                    <div className="h-3 bg-gray-200 rounded w-16" />
                  </div>
                </div>
                <div className="h-4 bg-gray-200 rounded w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (recentScans.length === 0 && recentBacktests.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-text-secondary">
            <Clock className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">No recent activity</p>
            <p className="text-xs mt-1">Run a scan or backtest to see results here</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {recentScans.length > 0 && (
          <div className="mb-4">
            <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wider mb-2">Scans</h4>
            {recentScans.map((scan) => (
              <ScanResultRow key={scan.id} entry={scan} />
            ))}
          </div>
        )}
        {recentBacktests.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wider mb-2">Backtests</h4>
            {recentBacktests.map((bt) => (
              <BacktestResultRow key={bt.id} entry={bt} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
})
