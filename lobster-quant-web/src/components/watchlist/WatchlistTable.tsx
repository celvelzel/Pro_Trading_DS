'use client'

import { memo } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useWatchlistStore } from '@/stores/watchlistStore'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Trash2,
  BarChart3,
  Plus,
} from 'lucide-react'

interface WatchlistStock {
  symbol: string
  name?: string
  price?: number
  change?: number
  changePercent?: number
  signal?: {
    type: 'bullish' | 'bearish' | 'neutral'
    score: number
  }
}

interface WatchlistTableProps {
  stocks: WatchlistStock[]
  loading?: boolean
  onAddClick?: () => void
  onCompareClick?: (symbols: string[]) => void
  className?: string
}

function SignalBadge({ type, score }: { type: string; score: number }) {
  const config = {
    bullish: { color: 'text-success bg-success/10', label: 'Bullish' },
    bearish: { color: 'text-error bg-error/10', label: 'Bearish' },
    neutral: { color: 'text-warning bg-warning/10', label: 'Neutral' },
  }

  const { color, label } = config[type as keyof typeof config] || config.neutral

  return (
    <span className={cn('px-2 py-1 rounded-full text-xs font-medium', color)}>
      {score}
    </span>
  )
}

export const WatchlistTable = memo(function WatchlistTable({
  stocks,
  loading = false,
  onAddClick,
  onCompareClick,
  className,
}: WatchlistTableProps) {
  const { selectedSymbols, toggleSelect, selectAll, deselectAll, removeSelected } =
    useWatchlistStore()

  const allSelected = stocks.length > 0 && selectedSymbols.length === stocks.length

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Watchlist</span>
            <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4 animate-pulse">
                <div className="h-4 w-4 bg-muted rounded" />
                <div className="h-4 w-16 bg-muted rounded" />
                <div className="flex-1" />
                <div className="h-4 w-20 bg-muted rounded" />
                <div className="h-4 w-16 bg-muted rounded" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span>Watchlist</span>
            <span className="text-sm font-normal text-text-secondary">
              {stocks.length} stocks
            </span>
          </div>
          <div className="flex items-center gap-2">
            {selectedSymbols.length > 0 && (
              <>
                <Button variant="outline" size="sm" onClick={deselectAll}>
                  Deselect All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onCompareClick?.(selectedSymbols)}
                  disabled={selectedSymbols.length < 2}
                >
                  <BarChart3 className="w-4 h-4 mr-1" />
                  Compare ({selectedSymbols.length})
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={removeSelected}
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Remove
                </Button>
              </>
            )}
            {selectedSymbols.length === 0 && (
              <Button variant="outline" size="sm" onClick={selectAll}>
                Select All
              </Button>
            )}
            <Button size="sm" onClick={onAddClick}>
              <Plus className="w-4 h-4 mr-1" />
              Add
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {stocks.length === 0 ? (
          <div className="text-center py-8 text-text-secondary">
            <p className="mb-2">No stocks in watchlist</p>
            <Button variant="outline" onClick={onAddClick}>
              <Plus className="w-4 h-4 mr-1" />
              Add Stock
            </Button>
          </div>
        ) : (
          <div className="space-y-1">
            {/* Header */}
            <div className="flex items-center gap-4 px-3 py-2 text-xs font-medium text-text-secondary border-b">
              <div className="w-4" />
              <div className="w-16">Symbol</div>
              <div className="flex-1">Name</div>
              <div className="w-20 text-right">Price</div>
              <div className="w-20 text-right">Change</div>
              <div className="w-16 text-center">Signal</div>
              <div className="w-8" />
            </div>

            {/* Rows */}
            {stocks.map((stock) => {
              const isSelected = selectedSymbols.includes(stock.symbol)
              const isPositive = (stock.change ?? 0) >= 0

              return (
                <div
                  key={stock.symbol}
                  className={cn(
                    'flex items-center gap-4 px-3 py-3 rounded-lg transition-colors',
                    isSelected
                      ? 'bg-primary/10 border border-primary/20'
                      : 'hover:bg-bg-hover'
                  )}
                >
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(stock.symbol)}
                    className="w-4 h-4 rounded border-gray-300"
                  />

                  {/* Symbol */}
                  <Link
                    href={`/analysis/${stock.symbol}`}
                    className="w-16 font-semibold text-text-primary hover:text-primary transition-colors"
                  >
                    {stock.symbol}
                  </Link>

                  {/* Name */}
                  <div className="flex-1 text-sm text-text-secondary truncate">
                    {stock.name || '-'}
                  </div>

                  {/* Price */}
                  <div className="w-20 text-right font-mono">
                    {stock.price ? `$${stock.price.toFixed(2)}` : '-'}
                  </div>

                  {/* Change */}
                  <div
                    className={cn(
                      'w-20 text-right font-mono text-sm',
                      isPositive ? 'text-success' : 'text-error'
                    )}
                  >
                    {stock.change !== undefined ? (
                      <div className="flex items-center justify-end gap-1">
                        {isPositive ? (
                          <TrendingUp className="w-3 h-3" />
                        ) : (
                          <TrendingDown className="w-3 h-3" />
                        )}
                        <span>
                          {isPositive ? '+' : ''}
                          {stock.changePercent?.toFixed(2)}%
                        </span>
                      </div>
                    ) : (
                      '-'
                    )}
                  </div>

                  {/* Signal */}
                  <div className="w-16 text-center">
                    {stock.signal ? (
                      <SignalBadge type={stock.signal.type} score={stock.signal.score} />
                    ) : (
                      '-'
                    )}
                  </div>

                  {/* Actions */}
                  <Link href={`/analysis/${stock.symbol}`}>
                    <Button variant="ghost" size="icon" className="w-8 h-8">
                      <BarChart3 className="w-4 h-4" />
                    </Button>
                  </Link>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
})
