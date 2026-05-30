'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MetricCard } from './MetricCard'
import { useStockData } from '@/hooks/useStock'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

const BENCHMARK_SYMBOLS = ['SPY', 'QQQ', 'DIA'] as const

interface MarketRowProps {
  symbol: string
}

function MarketRow({ symbol }: MarketRowProps) {
  const { data, isLoading, error } = useStockData(symbol)

  if (isLoading) {
    return (
      <div className="flex items-center justify-between py-2 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-12" />
        <div className="h-4 bg-gray-200 rounded w-16" />
        <div className="h-4 bg-gray-200 rounded w-20" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-between py-2 text-text-secondary">
        <span className="font-medium">{symbol}</span>
        <span className="text-sm">--</span>
        <span className="text-sm">--</span>
      </div>
    )
  }

  const isUp = data.change >= 0
  const DeltaIcon = isUp ? TrendingUp : data.change < 0 ? TrendingDown : Minus

  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <span className="font-semibold text-text-primary">{symbol}</span>
      <span className="text-text-primary">${data.price.toFixed(2)}</span>
      <div className={cn('flex items-center gap-1 text-sm font-medium', isUp ? 'text-success' : 'text-error')}>
        <DeltaIcon className="w-3 h-3" />
        <span>{isUp ? '+' : ''}{data.change.toFixed(2)} ({data.changePercent?.toFixed(2)}%)</span>
      </div>
    </div>
  )
}

export const MarketOverviewCard = memo(function MarketOverviewCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Market Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-0">
          {BENCHMARK_SYMBOLS.map((symbol) => (
            <MarketRow key={symbol} symbol={symbol} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
})
