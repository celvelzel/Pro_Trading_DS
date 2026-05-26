'use client'

import { useState } from 'react'
import { useStockData, useStockRisk, usePrefetchStock } from '@/hooks/useStock'
import { MetricCard } from '@/components/cards/MetricCard'
import { StatusCard } from '@/components/cards/StatusCard'
import { CandlestickChart } from '@/components/charts/CandlestickChart'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PrefetchLink } from '@/components/ui/prefetch-link'
import { STOCK_LISTS } from '@/lib/constants'
import { WatchlistTable } from '@/components/watchlist/WatchlistTable'
import { WatchlistAddDialog } from '@/components/watchlist/WatchlistAddDialog'
import { StockCompareView } from '@/components/watchlist/StockCompareView'
import { useWatchlistStore } from '@/stores/watchlistStore'

export default function DashboardPage() {
  // Fetch benchmark data (SPY)
  const { data: benchmark, isLoading: benchmarkLoading } = useStockData('SPY')
  const { data: risk, isLoading: riskLoading } = useStockRisk('SPY')
  const prefetchStock = usePrefetchStock()

  // Watchlist state
  const { symbols, addSymbol, removeSymbol, selectedSymbols, toggleSelect, deselectAll, removeSelected } = useWatchlistStore()
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [compareSymbols, setCompareSymbols] = useState<string[]>([])
  const [showCompare, setShowCompare] = useState(false)

  // Convert watchlist symbols to stock data (using mock data for now)
  const watchlistStocks = symbols.map((symbol) => ({
    symbol,
    name: undefined,
    price: undefined,
    change: undefined,
    changePercent: undefined,
    signal: undefined,
  }))

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Dashboard</h1>
        <p className="text-text-secondary mt-1">
          Market overview and quick analysis
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatusCard
          title="Market Condition"
          status={risk?.statusText || 'Loading...'}
          isGood={risk?.status === 'on'}
          details={
            risk?.reasons?.length
              ? `Reasons: ${risk.reasons.join(', ')}`
              : undefined
          }
          loading={riskLoading}
        />
        <MetricCard
          label="SPY Price"
          value={
            benchmark?.price
              ? `$${benchmark.price.toFixed(2)}`
              : 'Loading...'
          }
          delta={
            benchmark?.change
              ? `${benchmark.change >= 0 ? '+' : ''}${benchmark.change.toFixed(2)} (${benchmark.changePercent?.toFixed(2)}%)`
              : undefined
          }
          deltaType={
            benchmark?.change
              ? benchmark.change >= 0
                ? 'up'
                : 'down'
              : 'neutral'
          }
          loading={benchmarkLoading}
        />
        <MetricCard
          label="ON/OFF Ratio"
          value={
            risk
              ? `${risk.onPercent.toFixed(1)}% / ${risk.offPercent.toFixed(1)}%`
              : 'Loading...'
          }
          loading={riskLoading}
        />
      </div>

      {/* Price Chart */}
      <Card>
        <CardHeader>
          <CardTitle>SPY Price Chart</CardTitle>
        </CardHeader>
        <CardContent>
          {benchmark?.candles && benchmark.candles.length > 0 ? (
            <CandlestickChart
              data={benchmark.candles}
              symbol="SPY"
              height={400}
              showVolume={true}
            />
          ) : (
            <div className="h-[400px] flex items-center justify-center text-text-secondary">
              {benchmarkLoading ? 'Loading chart data...' : 'No chart data available'}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stock Comparison (conditional) */}
      {compareSymbols.length > 1 && (
        <StockCompareView
          symbols={compareSymbols}
          onClose={() => setCompareSymbols([])}
        />
      )}

      {/* Watchlist */}
      <WatchlistTable
        stocks={watchlistStocks}
        loading={false}
        onAddClick={() => setAddDialogOpen(true)}
        onCompareClick={(syms) => setCompareSymbols(syms)}
      />

      {/* Quick Access - Popular Stocks */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Access</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {STOCK_LISTS.US.slice(0, 10).map((symbol) => (
              <PrefetchLink
                key={symbol}
                symbol={symbol}
                href={`/analysis/${symbol}`}
                className="flex items-center justify-center p-3 rounded-lg border border-gray-200 hover:border-primary hover:bg-primary/5 transition-colors"
              >
                <span className="font-medium text-text-primary">{symbol}</span>
              </PrefetchLink>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Add to Watchlist Dialog */}
      <WatchlistAddDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onAdd={(symbol) => addSymbol(symbol)}
      />
    </div>
  )
}
