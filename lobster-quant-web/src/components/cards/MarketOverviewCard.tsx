'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
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
      <div className="flex items-center justify-between py-2">
        <Skeleton className="h-4 w-12" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-24" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-between py-2">
        <span className="font-mono text-sm font-semibold text-foreground">{symbol}</span>
        <span className="font-mono text-sm text-muted-foreground">--</span>
        <span className="font-mono text-sm text-muted-foreground">--</span>
      </div>
    )
  }

  const isUp = data.change >= 0
  const DeltaIcon = isUp ? TrendingUp : data.change < 0 ? TrendingDown : Minus

  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/50 py-2 last:border-0">
      <span className="font-mono text-sm font-semibold text-foreground">{symbol}</span>
      <span className="font-mono text-sm tabular-nums text-foreground">${data.price.toFixed(2)}</span>
      <div
        className={cn(
          'flex items-center gap-1 font-mono text-[13px] font-medium tabular-nums',
          isUp ? 'text-success' : 'text-error'
        )}
      >
        <DeltaIcon className="size-3.5" />
        <span>{isUp ? '+' : ''}{data.change.toFixed(2)} ({data.changePercent?.toFixed(2)}%)</span>
      </div>
    </div>
  )
}

export const MarketOverviewCard = memo(function MarketOverviewCard() {
  return (
    <Card className="transition-colors hover:border-primary/30">
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
