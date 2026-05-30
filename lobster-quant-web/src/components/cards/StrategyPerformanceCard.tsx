'use client'

import { memo, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useStrategyStore } from '@/stores/strategyStore'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus, AlertCircle, BarChart3 } from 'lucide-react'

function getSharpeColor(sharpe: number): string {
  if (sharpe >= 1.5) return 'text-success'
  if (sharpe >= 0.5) return 'text-primary'
  if (sharpe >= 0) return 'text-text-secondary'
  return 'text-error'
}

function getSharpeIcon(sharpe: number) {
  if (sharpe >= 0.5) return TrendingUp
  if (sharpe >= 0) return Minus
  return TrendingDown
}

export const StrategyPerformanceCard = memo(function StrategyPerformanceCard() {
  const { strategies, loading, error, fetchStrategies } = useStrategyStore()

  useEffect(() => {
    if (strategies.length === 0) {
      fetchStrategies()
    }
  }, [strategies.length, fetchStrategies])

  if (loading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <CardTitle>Strategy Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="h-4 bg-gray-200 rounded w-24" />
                <div className="h-4 bg-gray-200 rounded w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || strategies.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Strategy Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-text-secondary">
            <BarChart3 className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">{error || 'No strategies configured'}</p>
            <p className="text-xs mt-1">Create a strategy to see performance metrics</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
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
                className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
              >
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-primary" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">{strategy.name}</p>
                    <p className="text-xs text-text-secondary">{strategy.description || 'No description'}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-text-secondary">
                    {strategy.params.holdingDays}d hold · min {strategy.params.minScore}pts
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
