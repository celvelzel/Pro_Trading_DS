'use client'

import { memo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useWatchlistData } from '@/hooks/useWatchlistData'
import { useWatchlistStore } from '@/stores/watchlistStore'
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
    text: 'text-text-secondary',
    icon: Minus,
    label: 'Neutral',
  },
} as const

export const SignalSummaryCard = memo(function SignalSummaryCard() {
  const { stocks, isLoading } = useWatchlistData()
  const { symbols } = useWatchlistStore()

  if (symbols.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Signal Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-text-secondary">
            <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">No stocks in watchlist</p>
            <p className="text-xs mt-1">Add stocks to see signal indicators</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <CardTitle>Signal Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="h-4 bg-gray-200 rounded w-12" />
                <div className="h-6 bg-gray-200 rounded w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
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
                className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0"
              >
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-text-primary text-sm">{stock.symbol}</span>
                  {stock.price && (
                    <span className="text-xs text-text-secondary">${stock.price.toFixed(2)}</span>
                  )}
                </div>
                <div className={cn('flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium', style.bg, style.text)}>
                  <SignalIcon className="w-3 h-3" />
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
