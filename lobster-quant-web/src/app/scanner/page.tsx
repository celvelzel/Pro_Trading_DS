'use client'

import { useState, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useScanStocks, usePrefetchStock } from '@/hooks/useStock'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { SignalCard } from '@/components/cards/SignalCard'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { Search, Loader2 } from 'lucide-react'
import Link from 'next/link'
import type { Market, StockResult } from '@/lib/types'

/** Threshold above which virtualization kicks in */
const VIRTUALIZE_THRESHOLD = 50

export default function ScannerPage() {
  const [market, setMarket] = useState<Market>('US')
  const [minScore, setMinScore] = useState(60)
  const scanMutation = useScanStocks()
  const prefetchStock = usePrefetchStock()

  const handleScan = () => {
    scanMutation.mutate({ market, minScore })
  }

  const results = scanMutation.data?.results ?? []
  const shouldVirtualize = results.length > VIRTUALIZE_THRESHOLD

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Stock Scanner</h1>
        <p className="text-text-secondary mt-1">
          Scan stocks across multiple markets based on technical criteria
        </p>
      </div>

      {/* Scan Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Scan Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            {/* Market Selection */}
            <div className="flex-1">
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Market
              </label>
              <Select value={market} onValueChange={(value) => setMarket(value as Market)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select market" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="US">US Stocks</SelectItem>
                  <SelectItem value="HK">HK Stocks</SelectItem>
                  <SelectItem value="A">A-Shares</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Min Score Slider */}
            <div className="flex-1">
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Minimum Score: {minScore}
              </label>
              <Slider
                value={[minScore]}
                onValueChange={(value) => {
                  const val = Array.isArray(value) ? value[0] : value
                  setMinScore(val)
                }}
                max={100}
                min={0}
                step={5}
              />
            </div>

            {/* Scan Button */}
            <div className="flex items-end">
              <Button onClick={handleScan} disabled={scanMutation.isPending}>
                {scanMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4 mr-2" />
                    Scan Stocks
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error State */}
      {scanMutation.isError && (
        <ErrorState 
          message={scanMutation.error?.message || 'Failed to scan stocks'} 
          onRetry={() => scanMutation.mutate({ market, minScore })}
        />
      )}

      {/* Results */}
      {results.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-text-primary">
              Results ({results.length} stocks)
            </h2>
            {shouldVirtualize && (
              <p className="text-sm text-text-tertiary">
                Virtualized for performance
              </p>
            )}
          </div>

          {shouldVirtualize ? (
            <VirtualizedResultsGrid results={results} prefetchStock={prefetchStock} />
          ) : (
            <ResultsGrid results={results} prefetchStock={prefetchStock} />
          )}
        </div>
      )}

      {/* Empty State */}
      {scanMutation.isSuccess && results.length === 0 && (
        <EmptyState
          icon="search"
          title="No stocks found"
          message="Try lowering the minimum score or selecting a different market."
        />
      )}

      {/* Error State */}
      {scanMutation.isError && (
        <ErrorState
          message="Failed to scan stocks. Please try again."
          onRetry={handleScan}
        />
      )}
    </div>
  )
}

// ============================================================================
// Results Grid (non-virtualized, for < 50 items)
// ============================================================================

function ResultsGrid({
  results,
  prefetchStock,
}: {
  results: StockResult[]
  prefetchStock: (symbol: string) => void
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {results.map((stock) => (
        <StockResultCard
          key={stock.symbol}
          stock={stock}
          onHover={() => prefetchStock(stock.symbol)}
        />
      ))}
    </div>
  )
}

// ============================================================================
// Virtualized Results Grid (for 50+ items)
// ============================================================================

function VirtualizedResultsGrid({
  results,
  prefetchStock,
}: {
  results: StockResult[]
  prefetchStock: (symbol: string) => void
}) {
  const parentRef = useRef<HTMLDivElement>(null)

  const rowVirtualizer = useVirtualizer({
    count: results.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 180, // Estimated card height in px
    overscan: 5, // Render 5 extra rows above/below viewport
  })

  return (
    <div
      ref={parentRef}
      className="overflow-auto"
      style={{ height: '70vh' }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualRow) => {
          const stock = results[virtualRow.index]
          return (
            <div
              key={stock.symbol}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualRow.start}px)`,
              }}
              className="pb-4"
            >
              <StockResultCard
                stock={stock}
                onHover={() => prefetchStock(stock.symbol)}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Stock Result Card (shared between virtualized and non-virtualized)
// ============================================================================

function StockResultCard({
  stock,
  onHover,
}: {
  stock: StockResult
  onHover: () => void
}) {
  return (
    <Link
      href={`/analysis/${stock.symbol}`}
      onMouseEnter={onHover}
      onFocus={onHover}
      className="block"
    >
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="font-semibold text-text-primary">{stock.symbol}</p>
              <p className="text-sm text-text-secondary">{stock.name}</p>
            </div>
            <div className="text-right">
              <p className="font-semibold text-text-primary">
                ${stock.price.toFixed(2)}
              </p>
              <p
                className={`text-sm ${
                  (stock.change ?? 0) >= 0 ? 'text-success' : 'text-error'
                }`}
              >
                {(stock.change ?? 0) >= 0 ? '+' : ''}
                {(stock.change ?? 0).toFixed(2)} ({(stock.changePercent ?? 0).toFixed(2)}%)
              </p>
            </div>
          </div>
          <SignalCard
            signalType={stock.signalType}
            score={stock.score}
            probability={stock.probability}
            reasons={stock.reasons}
          />
        </CardContent>
      </Card>
    </Link>
  )
}
