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
import { AlertCircle } from 'lucide-react'

export default function DashboardPage() {
  // Timeframe state
  const [timeframe, setTimeframe] = useState<Timeframe>('1y')

  // Fetch benchmark data (SPY)
  const { data: benchmark, isLoading: benchmarkLoading, dataUpdatedAt: benchmarkUpdatedAt, error: benchmarkError } = useStockData('SPY')
  const { data: candles, isLoading: candlesLoading, error: candlesError } = useStockCandles('SPY', timeframe)
  const { data: risk, isLoading: riskLoading, error: riskError } = useStockRisk('SPY')

  // Watchlist state
  const { addSymbol } = useWatchlistStore()
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [compareSymbols, setCompareSymbols] = useState<string[]>([])

  // Fetch real-time data for watchlist stocks
  const { stocks: watchlistStocks, isLoading: watchlistLoading, refetch: refetchWatchlist } = useWatchlistData()

  // Check for errors
  const hasError = benchmarkError || candlesError || riskError
  const errorMessage = benchmarkError?.message || candlesError?.message || riskError?.message

  // If there's an error and no data, show error state
  if (hasError && !benchmark && !candles && !risk) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Dashboard</h1>
            <p className="text-text-secondary mt-1">
              Market overview and quick analysis
            </p>
          </div>
        </div>
        
        <Card className="border-error">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-8 w-8 text-error" />
              <div>
                <h3 className="text-lg font-semibold text-text-primary">Failed to load dashboard data</h3>
                <p className="text-text-secondary mt-1">
                  {errorMessage || 'Unable to fetch market data. Please check your connection and try again.'}
                </p>
                <button 
                  onClick={() => window.location.reload()} 
                  className="mt-3 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

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
          status={risk?.statusText || (riskError ? 'Error' : 'Loading...')}
          isGood={risk?.status === 'on'}
          details={
            riskError 
              ? `Error: ${riskError.message}`
              : risk?.reasons?.length
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
              : benchmarkError 
                ? 'Error'
                : 'Loading...'
          }
          delta={
            benchmarkError
              ? benchmarkError.message
              : benchmark?.change
                ? `${benchmark.change >= 0 ? '+' : ''}${benchmark.change.toFixed(2)} (${benchmark.changePercent?.toFixed(2)}%)`
                : undefined
          }
          deltaType={
            benchmarkError
              ? 'down'
              : benchmark?.change
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
              : riskError 
                ? 'Error'
                : 'Loading...'
          }
          delta={
            riskError ? riskError.message : undefined
          }
          deltaType={riskError ? 'down' : 'neutral'}
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
              {candlesLoading 
                ? 'Loading chart data...' 
                : candlesError 
                  ? `Error loading chart: ${candlesError.message}`
                  : 'No chart data available'}
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
