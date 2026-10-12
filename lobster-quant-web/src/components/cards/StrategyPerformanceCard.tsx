'use client'

import { memo, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useStrategyStore } from '@/stores/strategyStore'
import { BarChart3 } from 'lucide-react'

export const StrategyPerformanceCard = memo(function StrategyPerformanceCard() {
  const { strategies, loading, error, fetchStrategies } = useStrategyStore()

  useEffect(() => {
    if (strategies.length === 0) {
      fetchStrategies()
    }
  }, [strategies.length, fetchStrategies])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Strategy Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2.5">
                  <Skeleton className="size-7 rounded-md" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || strategies.length === 0) {
    return (
      <Card className="transition-colors hover:border-primary/30">
        <CardHeader>
          <CardTitle>Strategy Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
            <BarChart3 className="mb-2 size-8 opacity-50" />
            <p className="text-sm">{error || 'No strategies configured'}</p>
            <p className="mt-1 text-xs">Create a strategy to see performance metrics</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="transition-colors hover:border-primary/30">
      <CardHeader>
        <CardTitle>Strategy Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {strategies.map((strategy) => {
            // Note: Strategy store doesn't include metrics by default.
            // We show strategy info. Sharpe ratio comes from backtest history
            // or simulation performance which is fetched separately.
            return (
              <div
                key={strategy.id}
                className="flex items-center justify-between gap-3 border-b border-border/50 py-2 last:border-0"
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent">
                    <BarChart3 className="size-3.5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{strategy.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{strategy.description || 'No description'}</p>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs text-muted-foreground">
                    <span className="font-mono tabular-nums">{strategy.params.holdingDays}d</span> hold · min{' '}
                    <span className="font-mono tabular-nums">{strategy.params.minScore}pts</span>
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
})
