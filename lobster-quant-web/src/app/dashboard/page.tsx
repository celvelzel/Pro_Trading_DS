'use client'

import { useState } from 'react'
import { useStockData, useStockRisk, useStockCandles } from '@/hooks/useStock'
import { useWatchlistData } from '@/hooks/useWatchlistData'
import { MetricCard } from '@/components/cards/MetricCard'
import { StatusCard } from '@/components/cards/StatusCard'
import { CandlestickChart } from '@/components/charts/CandlestickChart'
import { TimeframeSelector, type Timeframe } from '@/components/charts/TimeframeSelector'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PrefetchLink } from '@/components/ui/prefetch-link'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { STOCK_LISTS } from '@/lib/constants'
import { WatchlistTable } from '@/components/watchlist/WatchlistTable'
import { WatchlistAddDialog } from '@/components/watchlist/WatchlistAddDialog'
import { StockCompareView } from '@/components/watchlist/StockCompareView'
import { useWatchlistStore } from '@/stores/watchlistStore'
import { formatDistanceToNow } from 'date-fns'

export default function DashboardPage() {
  // Timeframe state
  const [timeframe, setTimeframe] = useState<Timeframe>('1y')

  // Fetch benchmark data (SPY)
  const { data: benchmark, isLoading: benchmarkLoading, dataUpdatedAt: benchmarkUpdatedAt } = useStockData('SPY')
  const { data: candles, isLoading: candlesLoading } = useStockCandles('SPY', timeframe)
  const { data: risk, isLoading: riskLoading } = useStockRisk('SPY')

  // Watchlist state
  const { addSymbol } = useWatchlistStore()
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [compareSymbols, setCompareSymbols] = useState<string[]>([])

  // Fetch real-time data for watchlist stocks
  const { stocks: watchlistStocks, isLoading: watchlistLoading, refetch: refetchWatchlist } = useWatchlistData()

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold text-text-primary">Dashboard</h1>
            <HelpTooltip helpKey="dashboard.title" />
          </div>
          <p className="text-text-secondary mt-1">
            Market overview and quick analysis
          </p>
        </div>
        
        {/* Data Freshness Indicator */}
        {benchmarkUpdatedAt && (
          <div className="text-right">
            <p className="text-xs text-muted-foreground">
              Last updated: {formatDistanceToNow(new Date(benchmarkUpdatedAt), { addSuffix: true })}
            </p>
          </div>
        )}
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatusCard
          title={
            <div className="flex items-center gap-2">
              <span>Market Condition</span>
              <HelpTooltip helpKey="dashboard.market_status" />
            </div>
          }
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
          label={
            <div className="flex items-center gap-2">
              <span>ON/OFF Ratio</span>
              <HelpTooltip helpKey="dashboard.risk_metrics" />
            </div>
          }
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
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle>SPY Price Chart</CardTitle>
              <HelpTooltip helpKey="analysis.charts" />
            </div>
            <TimeframeSelector
              activeTimeframe={timeframe}
              onSelect={setTimeframe}
            />
          </div>
        </CardHeader>
        <CardContent>
          {candles && candles.length > 0 ? (
            <CandlestickChart
              data={candles}
              symbol="SPY"
              height={400}
              showVolume={true}
            />
          ) : (
            <div className="h-[400px] flex items-center justify-center text-text-secondary">
              {candlesLoading ? 'Loading chart data...' : 'No chart data available'}
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
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-lg font-semibold">Watchlist</h2>
        <HelpTooltip helpKey="dashboard.watchlist" />
      </div>
      <WatchlistTable
        stocks={watchlistStocks}
        loading={watchlistLoading}
        onAddClick={() => setAddDialogOpen(true)}
        onCompareClick={(syms) => setCompareSymbols(syms)}
        onRefresh={refetchWatchlist}
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
