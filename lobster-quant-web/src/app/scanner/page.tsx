'use client'

import { useState, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useScanStocksStream, usePrefetchStock } from '@/hooks/useStock'
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
import { ExportButton } from '@/components/ui/export-button'
import { PageHeader } from '@/components/layout/PageHeader'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import type { Market, StockResult } from '@/lib/types'

/** Threshold above which virtualization kicks in */
const VIRTUALIZE_THRESHOLD = 50

export default function ScannerPage() {
  const [market, setMarket] = useState<Market>('US')
  const [minScore, setMinScore] = useState(60)
  const { results, progress, isScanning, error, startScan } = useScanStocksStream()
  const prefetchStock = usePrefetchStock()

  const handleScan = () => {
    startScan({ market, minScore })
  }

  const shouldVirtualize = results.length > VIRTUALIZE_THRESHOLD

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      {/* Page Header */}
      <PageHeader
        title="Stock Scanner"
        description="Scan stocks across multiple markets based on technical criteria"
        actions={<HelpTooltip helpKey="scanner.title" />}
      />

      {/* Scan Controls */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <CardTitle>Scan Parameters</CardTitle>
            <HelpTooltip helpKey="scanner.scan_parameters" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
            {/* Market Selection */}
            <div className="w-full space-y-1.5 sm:w-48">
              <label className="block text-xs font-medium text-muted-foreground">
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
            <div className="min-w-56 flex-1 space-y-1.5">
              <label className="block text-xs font-medium text-muted-foreground">
                Minimum Score:{' '}
                <span className="font-mono font-semibold tabular-nums text-foreground">
                  {minScore}
                </span>
              </label>
              <div className="flex h-8 items-center">
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
            </div>

            {/* Scan Button */}
            <Button onClick={handleScan} disabled={isScanning}>
              {isScanning ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Search className="mr-2 size-4" />
                  Scan Stocks
                </>
              )}
            </Button>
          </div>

          {/* Progress Indicator */}
          {isScanning && progress && (
            <div className="mt-4 space-y-2 border-t border-border pt-4">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>
                  Scanning{' '}
                  <span className="font-mono font-medium text-foreground">
                    {progress.symbol}
                  </span>
                  {progress.status === 'skipped' && ' (skipped)'}
                  {progress.status === 'error' && ' (error)'}
                </span>
                <span className="font-mono tabular-nums">
                  {progress.processed} / {progress.total}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
                  style={{ width: `${(progress.processed / progress.total) * 100}%` }}
                />
              </div>
              {results.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-mono tabular-nums">{results.length}</span>{' '}
                  matching stock{results.length !== 1 ? 's' : ''} found so far
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorState
          message={error || 'Failed to scan stocks'}
          onRetry={handleScan}
        />
      )}

      {/* Results */}
      {results.length > 0 && (
        <div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold tracking-tight text-foreground">
                Results ({results.length} stocks)
              </h2>
              <HelpTooltip helpKey="scanner.results" />
            </div>
            <div className="flex items-center gap-2">
              <ExportButton
                data={results}
                columns={[
                  { key: 'symbol', header: 'Symbol' },
                  { key: 'name', header: 'Name' },
                  { key: 'price', header: 'Price', format: (v: number) => `$${v?.toFixed(2) ?? ''}` },
                  { key: 'change', header: 'Change', format: (v: number) => v?.toFixed(2) ?? '' },
                  { key: 'changePercent', header: 'Change %', format: (v: number) => `${v?.toFixed(2) ?? ''}%` },
                  { key: 'score', header: 'Score' },
                  { key: 'signalType', header: 'Signal' },
                  { key: 'probability', header: 'Probability', format: (v: number) => `${(v * 100)?.toFixed(1) ?? ''}%` },
                  { key: 'reasons', header: 'Reasons', format: (v: string[]) => v?.join('; ') ?? '' },
                ]}
                filename={`scanner-${market}`}
              />
              {shouldVirtualize && (
                <p className="text-xs text-muted-foreground">
                  Virtualized for performance
                </p>
              )}
            </div>
          </div>

          {shouldVirtualize ? (
            <VirtualizedResultsGrid results={results} prefetchStock={prefetchStock} />
          ) : (
            <ResultsGrid results={results} prefetchStock={prefetchStock} />
          )}
        </div>
      )}

      {/* Empty State — show only when scan finished with no results */}
      {!isScanning && !error && results.length === 0 && progress && (
        <EmptyState
          icon="search"
          title="No stocks found"
          message="Try lowering the minimum score or selecting a different market."
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
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
      className="overflow-auto rounded-lg"
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
      <Card className="h-full cursor-pointer transition-colors hover:border-primary/40">
        <CardContent className="p-4">
          <div className="mb-3 flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="font-mono font-semibold text-foreground">{stock.symbol}</p>
              <p className="truncate text-sm text-muted-foreground">{stock.name}</p>
            </div>
            <div className="text-right">
              <p className="font-mono font-semibold tabular-nums text-foreground">
                ${stock.price.toFixed(2)}
              </p>
              <p
                className={cn(
                  'font-mono text-sm tabular-nums',
                  (stock.change ?? 0) >= 0 ? 'text-success' : 'text-error'
                )}
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
