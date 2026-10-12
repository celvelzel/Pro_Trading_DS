'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useWatchlistData } from '@/hooks/useWatchlistData'
import { useSyncWatchlist } from '@/stores/watchlistStore'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react'

const SIGNAL_STYLES = {
  bullish: {
    bg: 'bg-success/10',
    text: 'text-success',
    icon: TrendingUp,
    label: 'Bullish',
  },
  bearish: {
    bg: 'bg-error/10',
    text: 'text-error',
    icon: TrendingDown,
    label: 'Bearish',
  },
  neutral: {
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    icon: Minus,
    label: 'Neutral',
  },
} as const

export const SignalSummaryCard = memo(function SignalSummaryCard() {
  const { stocks, isLoading } = useWatchlistData()
  const { symbols } = useSyncWatchlist()

  if (symbols.length === 0) {
    return (
      <Card className="transition-colors hover:border-primary/30">
        <CardHeader>
          <CardTitle>Signal Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
            <AlertCircle className="mb-2 size-8 opacity-50" />
            <p className="text-sm">No stocks in watchlist</p>
            <p className="mt-1 text-xs">Add stocks to see signal indicators</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Signal Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <Skeleton className="h-4 w-12" />
                <Skeleton className="h-6 w-16 rounded-full" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="transition-colors hover:border-primary/30">
      <CardHeader>
        <CardTitle>Signal Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {stocks.map((stock) => {
            const signalType = stock.signal?.type || 'neutral'
            const style = SIGNAL_STYLES[signalType]
            const SignalIcon = style.icon

            return (
              <div
                key={stock.symbol}
                className="flex items-center justify-between border-b border-border/50 py-1.5 last:border-0"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-semibold text-foreground">{stock.symbol}</span>
                  {stock.price && (
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">${stock.price.toFixed(2)}</span>
                  )}
                </div>
                <div className={cn('flex items-center gap-1.5 rounded-full px-2 py-1 font-mono text-xs font-medium tabular-nums', style.bg, style.text)}>
                  <SignalIcon className="size-3" />
                  <span>{stock.signal?.score ?? '--'}</span>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
})
