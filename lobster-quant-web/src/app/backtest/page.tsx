'use client'

import { useState, useCallback } from 'react'
import { useRunBacktest } from '@/hooks/useStock'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { MetricCard } from '@/components/cards/MetricCard'
import { TradeTable } from '@/components/cards/TradeTable'
import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import {
  FlaskConical,
  Play,
  TrendingUp,
  Target,
  AlertTriangle,
  BarChart3,
  Activity,
  Clock,
} from 'lucide-react'
import type { BacktestParams } from '@/lib/types'

// ============================================================================
// Skeleton Components
// ============================================================================

function MetricCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="animate-pulse">
          <CardContent className="p-4">
            <Skeleton className="h-3 w-16 mb-2" />
            <Skeleton className="h-7 w-20 mb-1" />
            <Skeleton className="h-3 w-12" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent>
        <div className="h-[400px] bg-muted/30 rounded-lg animate-pulse flex items-center justify-center">
          <Activity className="w-8 h-8 text-muted-foreground/30" />
        </div>
      </CardContent>
    </Card>
  )
}

function TableSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-28" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex gap-4">
              <Skeleton className="h-4 w-8" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-12" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Main Page
// ============================================================================

export default function BacktestPage() {
  // Form state
  const [symbol, setSymbol] = useState('SPY')
  const [holdingDays, setHoldingDays] = useState(10)
  const [minScore, setMinScore] = useState(60)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [slippagePct, setSlippagePct] = useState('0.1')
  const [commissionPct, setCommissionPct] = useState('0.1')

  const backtestMutation = useRunBacktest()

  const handleRun = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()

      const params: BacktestParams = {
        symbol: symbol.toUpperCase(),
        holdingDays,
        minScore,
      }

      if (startDate) params.startDate = startDate
      if (endDate) params.endDate = endDate

      // Convert percentage to decimal (0.1% -> 0.001)
      const slippage = parseFloat(slippagePct)
      if (!isNaN(slippage) && slippage > 0) {
        params.slippagePct = slippage / 100
      }

      const commission = parseFloat(commissionPct)
      if (!isNaN(commission) && commission > 0) {
        params.commissionPct = commission / 100
      }

      backtestMutation.mutate(params)
    },
    [symbol, holdingDays, minScore, startDate, endDate, slippagePct, commissionPct, backtestMutation]
  )

  const result = backtestMutation.data
  const isLoading = backtestMutation.isPending
  const hasResult = !!result && !isLoading

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 bg-primary/10 rounded-lg">
          <FlaskConical className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Strategy Backtest</h1>
          <p className="text-text-secondary mt-0.5">
            Test your trading strategy with historical data
          </p>
        </div>
      </div>

      {/* ================================================================ */}
      {/* Config Form                                                       */}
      {/* ================================================================ */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Backtest Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRun} className="space-y-6">
            {/* Row 1: Core params */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Symbol */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Stock Symbol
                </label>
                <Input
                  type="text"
                  placeholder="e.g., SPY, AAPL, TSLA"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  required
                  className="font-mono"
                />
              </div>

              {/* Holding Days */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Holding Days:{' '}
                  <span className="text-text-primary font-semibold">{holdingDays}</span>
                </label>
                <Slider
                  value={[holdingDays]}
                  onValueChange={(value) => {
                    const val = Array.isArray(value) ? value[0] : value
                    setHoldingDays(val)
                  }}
                  min={5}
                  max={60}
                  step={5}
                  className="mt-2"
                />
                <div className="flex justify-between text-xs text-text-tertiary mt-1">
                  <span>5d</span>
                  <span>60d</span>
                </div>
              </div>

              {/* Min Score */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Min Score:{' '}
                  <span className="text-text-primary font-semibold">{minScore}</span>
                </label>
                <Slider
                  value={[minScore]}
                  onValueChange={(value) => {
                    const val = Array.isArray(value) ? value[0] : value
                    setMinScore(val)
                  }}
                  min={30}
                  max={90}
                  step={5}
                  className="mt-2"
                />
                <div className="flex justify-between text-xs text-text-tertiary mt-1">
                  <span>30</span>
                  <span>90</span>
                </div>
              </div>
            </div>

            {/* Row 2: Date range & costs */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Start Date */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Start Date{' '}
                  <span className="text-text-tertiary font-normal">(optional)</span>
                </label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="font-mono text-sm"
                />
              </div>

              {/* End Date */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  End Date{' '}
                  <span className="text-text-tertiary font-normal">(optional)</span>
                </label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="font-mono text-sm"
                />
              </div>

              {/* Slippage */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Slippage %{' '}
                  <span className="text-text-tertiary font-normal">(per trade)</span>
                </label>
                <Input
                  type="number"
                  value={slippagePct}
                  onChange={(e) => setSlippagePct(e.target.value)}
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="0.1"
                  className="font-mono text-sm"
                />
              </div>

              {/* Commission */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Commission %{' '}
                  <span className="text-text-tertiary font-normal">(per trade)</span>
                </label>
                <Input
                  type="number"
                  value={commissionPct}
                  onChange={(e) => setCommissionPct(e.target.value)}
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="0.1"
                  className="font-mono text-sm"
                />
              </div>
            </div>

            {/* Run Button */}
            <div className="flex items-center gap-4">
              <Button
                type="submit"
                disabled={isLoading || !symbol.trim()}
                className="min-w-[140px]"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Run Backtest
                  </>
                )}
              </Button>

              {backtestMutation.isError && (
                <p className="text-sm text-error flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" />
                  {backtestMutation.error?.message || 'Backtest failed. Check parameters.'}
                </p>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* ================================================================ */}
      {/* Results Section                                                   */}
      {/* ================================================================ */}

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-6">
          <MetricCardsSkeleton />
          <ChartSkeleton />
          <TableSkeleton />
        </div>
      )}

      {/* Error State */}
      {backtestMutation.isError && !isLoading && (
        <Card className="border-error/20 bg-error/5">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="w-8 h-8 text-error mx-auto mb-2" />
            <p className="text-text-primary font-medium">Backtest Failed</p>
            <p className="text-sm text-text-secondary mt-1">
              {backtestMutation.error?.message || 'An unexpected error occurred. Please try again.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {hasResult && (
        <div className="space-y-6">
          {/* Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <MetricCard
              label="Total Trades"
              value={result.totalTrades.toString()}
              delta={`${result.trades.length} executed`}
              deltaType="neutral"
            />
            <MetricCard
              label="Win Rate"
              value={`${result.winRate.toFixed(1)}%`}
              delta={result.winRate >= 50 ? 'Above 50%' : 'Below 50%'}
              deltaType={result.winRate >= 50 ? 'up' : 'down'}
            />
            <MetricCard
              label="Total Return"
              value={`${result.totalReturn >= 0 ? '+' : ''}${result.totalReturn.toFixed(2)}%`}
              delta={result.totalReturn >= 0 ? 'Profitable' : 'Loss'}
              deltaType={result.totalReturn >= 0 ? 'up' : 'down'}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={result.sharpeRatio.toFixed(2)}
              delta={
                result.sharpeRatio >= 1
                  ? 'Excellent'
                  : result.sharpeRatio >= 0.5
                    ? 'Good'
                    : 'Poor'
              }
              deltaType={
                result.sharpeRatio >= 1
                  ? 'up'
                  : result.sharpeRatio >= 0.5
                    ? 'neutral'
                    : 'down'
              }
            />
            <MetricCard
              label="Max Drawdown"
              value={`${result.maxDrawdown.toFixed(2)}%`}
              delta={result.maxDrawdown < 10 ? 'Low risk' : result.maxDrawdown < 25 ? 'Moderate' : 'High risk'}
              deltaType={result.maxDrawdown < 10 ? 'up' : result.maxDrawdown < 25 ? 'neutral' : 'down'}
            />
            <MetricCard
              label="Avg Hold"
              value={
                result.trades.length > 0
                  ? `${Math.round(
                      result.trades.reduce((sum, t) => sum + t.holdingDays, 0) /
                        result.trades.length
                    )}d`
                  : 'N/A'
              }
              delta={
                result.trades.length > 0
                  ? `${Math.min(...result.trades.map((t) => t.holdingDays))}–${Math.max(
                      ...result.trades.map((t) => t.holdingDays)
                    )}d range`
                  : undefined
              }
              deltaType="neutral"
            />
          </div>

          {/* Equity Curve Chart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  Equity Curve
                </CardTitle>
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <Clock className="w-3.5 h-3.5" />
                  <span>
                    {result.equityCurve.length > 0 && (
                      <>
                        {result.equityCurve[0].date} →{' '}
                        {result.equityCurve[result.equityCurve.length - 1].date}
                      </>
                    )}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <EquityCurveChart data={result.equityCurve} height={400} />
            </CardContent>
          </Card>

          {/* Trade History Table */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Trade History
                </CardTitle>
                <span className="text-sm text-text-secondary">
                  {result.trades.length} trade{result.trades.length !== 1 ? 's' : ''}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <TradeTable trades={result.trades} />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty State - No results yet */}
      {!isLoading && !backtestMutation.isError && !hasResult && (
        <Card className="border-dashed">
          <CardContent className="p-12 text-center">
            <FlaskConical className="w-12 h-12 text-text-tertiary mx-auto mb-4" />
            <p className="text-lg font-medium text-text-primary">
              Configure & Run Your Backtest
            </p>
            <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
              Set your strategy parameters above and click &quot;Run Backtest&quot; to analyze
              historical performance with equity curves, trade history, and key metrics.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
