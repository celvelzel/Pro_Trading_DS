'use client'

import { useState, Suspense, lazy } from 'react'
import { useDashboardData } from '@/hooks/useDashboardData'
import { MetricCard } from '@/components/cards/MetricCard'
import { StatusCard } from '@/components/cards/StatusCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PrefetchLink } from '@/components/ui/prefetch-link'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { STOCK_LISTS } from '@/lib/constants'
import { WatchlistTable } from '@/components/watchlist/WatchlistTable'
import { WatchlistAddDialog } from '@/components/watchlist/WatchlistAddDialog'
import { StockCompareView } from '@/components/watchlist/StockCompareView'
import { formatDistanceToNow } from 'date-fns'
import { Skeleton } from '@/components/ui/skeleton'
import { DashboardSkeleton } from '@/components/skeletons/DashboardSkeleton'
import { ErrorDisplay } from '@/components/ui/error-display'
import type { Timeframe } from '@/components/charts/TimeframeSelector'
import { PageHeader } from '@/components/layout/PageHeader'

// Lazy load heavy widgets
const MarketOverviewCard = lazy(() => import('@/components/cards/MarketOverviewCard').then(m => ({ default: m.MarketOverviewCard })))
const SignalSummaryCard = lazy(() => import('@/components/cards/SignalSummaryCard').then(m => ({ default: m.SignalSummaryCard })))
const RecentActivityCard = lazy(() => import('@/components/cards/RecentActivityCard').then(m => ({ default: m.RecentActivityCard })))
const StrategyPerformanceCard = lazy(() => import('@/components/cards/StrategyPerformanceCard').then(m => ({ default: m.StrategyPerformanceCard })))
const QuickActionsCard = lazy(() => import('@/components/cards/QuickActionsCard').then(m => ({ default: m.QuickActionsCard })))
const SignalFeedCard = lazy(() => import('@/components/cards/SignalFeedCard').then(m => ({ default: m.SignalFeedCard })))
const CandlestickChart = lazy(() => import('@/components/charts/CandlestickChart').then(m => ({ default: m.CandlestickChart })))
const TimeframeSelector = lazy(() => import('@/components/charts/TimeframeSelector').then(m => ({ default: m.TimeframeSelector })))

function WidgetSkeleton() {
  return (
    <Card className="animate-in fade-in duration-300">
      <CardHeader className="pb-2">
        <Skeleton className="h-5 w-36" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/6" />
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Loading progress bar shown during initial data fetch.
 * Displays a thin animated bar at the top of the page.
 */
function LoadingProgressBar({ progress }: { progress: number }) {
  return (
    <div className="fixed left-0 right-0 top-0 z-50 h-0.5 bg-muted">
      <div
        className="h-full bg-primary transition-all duration-500 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}

export default function DashboardPage() {
  // Timeframe state
  const [timeframe, setTimeframe] = useState<Timeframe>('1y')

  // Centralized data fetching with parallel queries
  const {
    benchmark,
    candles,
    risk,
    watchlistStocks,
    refetchWatchlist,
    isLoading,
    isInitialLoad,
    loadingProgress,
    hasError,
    errors,
    errorMessage,
    loadingStates,
    lastUpdated,
  } = useDashboardData(timeframe)

  // Watchlist state
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [compareSymbols, setCompareSymbols] = useState<string[]>([])

  // Show full skeleton on initial load (no data cached yet)
  if (isInitialLoad) {
    return (
      <>
        <LoadingProgressBar progress={loadingProgress} />
        <DashboardSkeleton />
      </>
    )
  }

  // Show full-page error only if ALL queries failed with no cached data
  const allFailed = hasError && !benchmark && !candles && !risk
  if (allFailed) {
    return (
      <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
        <PageHeader
          title="Dashboard"
          description="Market overview and quick analysis"
        />
        <ErrorDisplay
          error={errors.benchmark || errors.candles || errors.risk}
          onRetry={() => window.location.reload()}
          retryLabel="Reload Dashboard"
          variant="card"
        />
      </div>
    )
  }

  return (
    <>
      {/* Show progress bar while any query is still loading */}
      {isLoading && <LoadingProgressBar progress={loadingProgress} />}

      <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
        {/* Page header */}
        <PageHeader
          title="Dashboard"
          description="Market overview and quick analysis"
          actions={
            <>
              <HelpTooltip helpKey="dashboard.title" />
              {lastUpdated && (
                <span className="rounded-full border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground">
                  Updated{' '}
                  {formatDistanceToNow(new Date(lastUpdated), {
                    addSuffix: true,
                  })}
                </span>
              )}
            </>
          }
        />

        {/* Key market status */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatusCard
            title={
              <div className="flex items-center gap-2">
                <span>Market Condition</span>
                <HelpTooltip helpKey="dashboard.market_status" />
              </div>
            }
            status={risk?.statusText || (errors.risk ? 'Error' : 'Loading...')}
            isGood={risk?.status === 'on'}
            details={
              errors.risk
                ? `Error: ${errors.risk.message}`
                : risk?.reasons?.length
                  ? `Reasons: ${risk.reasons.join(', ')}`
                  : undefined
            }
            loading={loadingStates.risk}
          />
          <MetricCard
            label="SPY Price"
            value={
              benchmark?.price
                ? `$${benchmark.price.toFixed(2)}`
                : errors.benchmark
                  ? 'Error'
                  : 'Loading...'
            }
            delta={
              errors.benchmark
                ? errors.benchmark.message
                : benchmark?.change
                  ? `${benchmark.change >= 0 ? '+' : ''}${benchmark.change.toFixed(2)} (${benchmark.changePercent?.toFixed(2)}%)`
                  : undefined
            }
            deltaType={
              errors.benchmark
                ? 'down'
                : benchmark?.change
                  ? benchmark.change >= 0
                    ? 'up'
                    : 'down'
                  : 'neutral'
            }
            loading={loadingStates.benchmark}
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
                : errors.risk
                  ? 'Error'
                  : 'Loading...'
            }
            delta={errors.risk ? errors.risk.message : undefined}
            deltaType={errors.risk ? 'down' : 'neutral'}
            loading={loadingStates.risk}
          />
        </div>

        {/* Inline error banner for partial failures (data available but some queries errored) */}
        {hasError && (benchmark || candles || risk) && (
          <ErrorDisplay
            error={errorMessage}
            variant="simple"
            className="text-sm"
          />
        )}

        {/* Information widgets */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Suspense fallback={<WidgetSkeleton />}>
            <MarketOverviewCard />
          </Suspense>
          <Suspense fallback={<WidgetSkeleton />}>
            <SignalSummaryCard />
          </Suspense>
          <Suspense fallback={<WidgetSkeleton />}>
            <RecentActivityCard />
          </Suspense>
          <Suspense fallback={<WidgetSkeleton />}>
            <StrategyPerformanceCard />
          </Suspense>
          <Suspense fallback={<WidgetSkeleton />}>
            <QuickActionsCard />
          </Suspense>
          <Suspense fallback={<WidgetSkeleton />}>
            <SignalFeedCard />
          </Suspense>
        </div>

        {/* Price chart */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2">
                <CardTitle>SPY Price Chart</CardTitle>
                <HelpTooltip helpKey="analysis.charts" />
              </div>
              <Suspense fallback={<Skeleton className="h-8 w-48" />}>
                <TimeframeSelector
                  activeTimeframe={timeframe}
                  onSelect={setTimeframe}
                />
              </Suspense>
            </div>
          </CardHeader>
          <CardContent className="px-2 sm:px-4">
            <Suspense fallback={<Skeleton className="h-[300px] w-full sm:h-[400px]" />}>
              {candles ? (
                <div className="h-[300px] sm:h-[400px]">
                  <CandlestickChart
                    data={candles}
                    symbol="SPY"
                    height={undefined}
                    showVolume={true}
                  />
                </div>
              ) : (
                <div className="flex h-[400px] items-center justify-center text-sm text-muted-foreground">
                  {loadingStates.candles
                    ? 'Loading chart data...'
                    : errors.candles
                      ? `Error loading chart: ${errors.candles.message}`
                      : 'No chart data available'}
                </div>
              )}
            </Suspense>
          </CardContent>
        </Card>

        {/* Stock comparison (conditional) */}
        {compareSymbols.length > 1 && (
          <StockCompareView
            symbols={compareSymbols}
            onClose={() => setCompareSymbols([])}
          />
        )}

        {/* Watchlist */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold tracking-tight">Watchlist</h2>
            <HelpTooltip helpKey="dashboard.watchlist" />
          </div>
          <WatchlistTable
            stocks={watchlistStocks}
            loading={loadingStates.watchlist}
            onAddClick={() => setAddDialogOpen(true)}
            onCompareClick={(syms) => setCompareSymbols(syms)}
            onRefresh={refetchWatchlist}
          />
        </div>

        {/* Quick access — popular symbols */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Access</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
              {STOCK_LISTS.US.slice(0, 10).map((symbol) => (
                <PrefetchLink
                  key={symbol}
                  symbol={symbol}
                  href={`/analysis/${symbol}`}
                  className="flex items-center justify-center rounded-md border border-border bg-background p-3 font-mono text-sm font-medium text-foreground transition-colors hover:border-primary/50 hover:bg-primary/5 hover:text-primary"
                >
                  {symbol}
                </PrefetchLink>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Add to watchlist dialog */}
        <WatchlistAddDialog
          open={addDialogOpen}
          onOpenChange={setAddDialogOpen}
        />
      </div>
    </>
  )
}
