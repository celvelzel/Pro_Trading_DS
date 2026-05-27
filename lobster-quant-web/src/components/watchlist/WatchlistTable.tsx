'use client'

import { memo } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useWatchlistStore } from '@/stores/watchlistStore'
import type { WatchlistStockData } from '@/hooks/useWatchlistData'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Trash2,
  BarChart3,
  Plus,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'

interface WatchlistTableProps {
  stocks: WatchlistStockData[]
  loading?: boolean
  onAddClick?: () => void
  onCompareClick?: (symbols: string[]) => void
  onRefresh?: () => void
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

function PriceChange({ change, changePercent }: { change?: number; changePercent?: number }) {
  if (change === undefined || changePercent === undefined) {
    return <span className="text-text-tertiary text-sm">--</span>
  }

  const isPositive = change >= 0
  const Icon = isPositive ? TrendingUp : TrendingDown

  return (
    <div className={cn('flex items-center gap-1', isPositive ? 'text-success' : 'text-error')}>
      <Icon className="w-3 h-3" />
      <span className="text-sm font-medium">
        {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
      </span>
    </div>
  )
}

function StockRowSkeleton() {
  return (
    <div className="flex items-center gap-4 py-3 animate-pulse">
      <div className="h-4 w-4 bg-muted rounded" />
      <div className="h-4 w-16 bg-muted rounded" />
      <div className="flex-1" />
      <div className="h-4 w-24 bg-muted rounded" />
      <div className="h-4 w-20 bg-muted rounded" />
      <div className="h-6 w-12 bg-muted rounded-full" />
    </div>
  )
}

function StockRow({ stock }: { stock: WatchlistStockData }) {
  const { selectedSymbols, toggleSelect } = useWatchlistStore()
  const isSelected = selectedSymbols.includes(stock.symbol)

  if (stock.isLoading) {
    return <StockRowSkeleton />
  }

  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-b-0">
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={isSelected}
        onChange={() => toggleSelect(stock.symbol)}
        className="h-4 w-4 rounded border-gray-300"
      />

      {/* Symbol */}
      <Link
        href={`/analysis/${stock.symbol}`}
        className="font-medium text-text-primary hover:text-primary transition-colors min-w-[60px]"
      >
        {stock.symbol}
      </Link>

      <div className="flex-1" />

      {/* Price */}
      <div className="text-right min-w-[80px]">
        {stock.price !== undefined ? (
          <span className="font-mono text-text-primary">${stock.price.toFixed(2)}</span>
        ) : (
          <span className="text-text-tertiary">--</span>
        )}
      </div>

      {/* Change */}
      <div className="min-w-[120px]">
        <PriceChange change={stock.change} changePercent={stock.changePercent} />
      </div>

      {/* Signal */}
      <div className="min-w-[60px]">
        {stock.signal ? (
          <SignalBadge type={stock.signal.type} score={stock.signal.score} />
        ) : stock.error ? (
          <div className="flex items-center gap-1 text-error" title={stock.error}>
            <AlertCircle className="w-4 h-4" />
            <span className="text-xs">Error</span>
          </div>
        ) : (
          <span className="text-text-tertiary text-sm">--</span>
        )}
      </div>
    </div>
  )
}

export const WatchlistTable = memo(function WatchlistTable({
  stocks,
  loading = false,
  onAddClick,
  onCompareClick,
  onRefresh,
  className,
}: WatchlistTableProps) {
  const { selectedSymbols, selectAll, deselectAll, removeSelected } =
    useWatchlistStore()

  const allSelected = stocks.length > 0 && selectedSymbols.length === stocks.length

  if (loading && stocks.length === 0) {
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
              <StockRowSkeleton key={i} />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (stocks.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Watchlist</span>
            <Button variant="outline" size="sm" onClick={onAddClick}>
              <Plus className="w-4 h-4 mr-1" />
              Add Stock
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-text-tertiary">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium mb-2">No stocks in watchlist</p>
            <p className="text-sm">Add stocks to track their prices and signals</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>Watchlist</span>
            <span className="text-sm font-normal text-text-tertiary">
              ({stocks.length} {stocks.length === 1 ? 'stock' : 'stocks'})
            </span>
            {loading && (
              <RefreshCw className="w-4 h-4 text-text-tertiary animate-spin" />
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Refresh button */}
            {onRefresh && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                disabled={loading}
                title="Refresh data"
              >
                <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
              </Button>
            )}

            {/* Compare button */}
            {selectedSymbols.length > 1 && onCompareClick && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onCompareClick(selectedSymbols)}
              >
                <BarChart3 className="w-4 h-4 mr-1" />
                Compare ({selectedSymbols.length})
              </Button>
            )}

            {/* Select/Deselect all */}
            <Button variant="ghost" size="sm" onClick={allSelected ? deselectAll : selectAll}>
              {allSelected ? 'Deselect All' : 'Select All'}
            </Button>

            {/* Remove selected */}
            {selectedSymbols.length > 0 && (
              <Button variant="destructive" size="sm" onClick={removeSelected}>
                <Trash2 className="w-4 h-4 mr-1" />
                Remove ({selectedSymbols.length})
              </Button>
            )}

            {/* Add button */}
            <Button variant="outline" size="sm" onClick={onAddClick}>
              <Plus className="w-4 h-4 mr-1" />
              Add
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="divide-y">
          {stocks.map((stock) => (
            <StockRow key={stock.symbol} stock={stock} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
})
