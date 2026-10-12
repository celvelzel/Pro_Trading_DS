'use client'

import Link from 'next/link'
import { useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import {
  useStockData,
  useStockCandles,
  useStockIndicators,
  useStockSignals,
  useStockSignalHistory,
  useStockOptions,
  useStockRisk,
} from '@/hooks/useStock'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { MetricCard } from '@/components/cards/MetricCard'
import { SignalCard } from '@/components/cards/SignalCard'
import { StatusCard } from '@/components/cards/StatusCard'
import { AnnotatedCandlestickChart } from '@/components/charts/AnnotatedCandlestickChart'
import { ChartSkeleton } from '@/components/charts/ChartSkeleton'
import { IndicatorToggle, type IndicatorType } from '@/components/charts/IndicatorToggle'
import { SignalHistoryChart } from '@/components/charts/SignalHistoryChart'
import { MultiTimeframeChart } from '@/components/charts/MultiTimeframeChart'
import { ScoreRadarChart } from '@/components/charts/ScoreRadarChart'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, BarChart3, Activity, Shield, Layers } from 'lucide-react'

export default function AnalysisDetailPage() {
  const params = useParams()
  const symbol = params.symbol as string

  // Indicator toggle state
  const [activeIndicators, setActiveIndicators] = useState<IndicatorType[]>([])

  const handleIndicatorToggle = useCallback((indicator: IndicatorType) => {
    setActiveIndicators((prev) =>
      prev.includes(indicator)
        ? prev.filter((i) => i !== indicator)
        : [...prev, indicator]
    )
  }, [])

  // Fetch all data for the stock
  // useStockData: full data for header display (price, name, change, volume)
  const { data: stock, isLoading: stockLoading } = useStockData(symbol)
  // useStockCandles: uses `select` to extract only candles for the chart.
  // This prevents chart re-renders when price/metadata changes but candles don't.
  const { data: candles } = useStockCandles(symbol)
  const { data: indicators, isLoading: indicatorsLoading } = useStockIndicators(symbol)
  const { data: signals, isLoading: signalsLoading } = useStockSignals(symbol)
  const { data: signalHistory } = useStockSignalHistory(symbol)
  const { data: options, isLoading: optionsLoading } = useStockOptions(symbol)
  const { data: risk, isLoading: riskLoading } = useStockRisk(symbol)

  // Multi-timeframe candle data
  const { data: candles1w } = useStockCandles(symbol, '1w')
  const { data: candles1m } = useStockCandles(symbol, '1m')
  const { data: candles3m } = useStockCandles(symbol, '3m')
  const { data: candles6m } = useStockCandles(symbol, '6m')

  // Loading state
  if (stockLoading) {
    return (
      <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
        <div className="space-y-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <ChartSkeleton height={400} />
      </div>
    )
  }

  // Error state
  if (!stock) {
    return (
      <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
        <Card className="border-error/50">
          <CardContent className="p-6 text-center">
            <p className="text-lg text-error">Failed to load data for {symbol}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Analysis', href: '/analysis' },
          { label: symbol },
        ]}
      />

      {/* Price Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Link
              className="text-sm text-primary underline underline-offset-4"
              href={{ pathname: "/copilot", query: { workflow: "market", symbol } }}
            >
              此标的 Market 合成只读演示
            </Link>
            <h1 className="font-mono text-2xl font-bold tracking-tight text-foreground">
              {symbol}
            </h1>
            <HelpTooltip helpKey="analysis.title" />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{stock.name}</p>
        </div>
        <div className="shrink-0 md:text-right">
          <p className="font-mono text-3xl font-bold tabular-nums text-foreground">
            ${stock.price.toFixed(2)}
          </p>
          <div
            className={cn(
              'mt-1 flex items-center gap-1 font-mono text-sm font-medium tabular-nums md:justify-end',
              (stock.change ?? 0) >= 0 ? 'text-success' : 'text-error'
            )}
          >
            {(stock.change ?? 0) >= 0 ? (
              <TrendingUp className="size-4" />
            ) : (
              <TrendingDown className="size-4" />
            )}
            <span>
              {(stock.change ?? 0) >= 0 ? '+' : ''}
              {(stock.change ?? 0).toFixed(2)} ({(stock.changePercent ?? 0).toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Volume"
          value={`${(stock.volume / 1000000).toFixed(1)}M`}
          loading={stockLoading}
        />
        <MetricCard
          label="RSI"
          value={indicators ? indicators.rsi.toFixed(1) : '...'}
          deltaType={
            indicators
              ? indicators.rsi > 70
                ? 'down'
                : indicators.rsi < 30
                  ? 'up'
                  : 'neutral'
              : 'neutral'
          }
          loading={indicatorsLoading}
        />
        <MetricCard
          label="ATR %"
          value={indicators ? `${indicators.atrPercent.toFixed(2)}%` : '...'}
          loading={indicatorsLoading}
        />
        <MetricCard
          label="Signal Score"
          value={signals ? `${signals.score}/100` : '...'}
          deltaType={
            signals
              ? signals.type === 'bullish'
                ? 'up'
                : signals.type === 'bearish'
                  ? 'down'
                  : 'neutral'
              : 'neutral'
          }
          loading={signalsLoading}
        />
      </div>

      {/* Tabs for different analysis sections */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="size-4" />
            <span className="hidden md:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="technical" className="flex items-center gap-2">
            <Activity className="size-4" />
            <span className="hidden md:inline">Technical</span>
          </TabsTrigger>
          <TabsTrigger value="options" className="flex items-center gap-2">
            <TrendingUp className="size-4" />
            <span className="hidden md:inline">Options</span>
          </TabsTrigger>
          <TabsTrigger value="signals" className="flex items-center gap-2">
            <TrendingUp className="size-4" />
            <span className="hidden md:inline">Signals</span>
          </TabsTrigger>
          <TabsTrigger value="risk" className="flex items-center gap-2">
            <Shield className="size-4" />
            <span className="hidden md:inline">Risk</span>
          </TabsTrigger>
          <TabsTrigger value="multi-tf" className="flex items-center gap-2">
            <Layers className="size-4" />
            <span className="hidden md:inline">Multi-TF</span>
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <CardTitle>Price Chart</CardTitle>
                  <HelpTooltip helpKey="analysis.charts" />
                </div>
                <IndicatorToggle
                  activeIndicators={activeIndicators}
                  onToggle={handleIndicatorToggle}
                />
              </div>
            </CardHeader>
            <CardContent className="px-2 sm:px-4">
              {candles && candles.length > 0 ? (
                <AnnotatedCandlestickChart
                  data={candles}
                  symbol={symbol}
                  height={500}
                  showVolume={true}
                  activeIndicators={activeIndicators}
                />
              ) : (
                <div className="flex h-[400px] items-center justify-center text-sm text-muted-foreground">
                  No chart data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Signal Summary & Score Decomposition */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              {signals && (
                <SignalCard
                  signalType={signals.type}
                  score={signals.score}
                  probability={signals.probability}
                  reasons={signals.reasons}
                  loading={signalsLoading}
                  className="h-full"
                />
              )}
            </div>
            <ScoreRadarChart
              loading={signalsLoading}
              className="h-full"
            />
          </div>
        </TabsContent>

        {/* Technical Tab */}
        <TabsContent value="technical" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="RSI (14)"
              value={indicators ? indicators.rsi.toFixed(2) : '...'}
              delta={
                indicators
                  ? indicators.rsi > 70
                    ? 'Overbought'
                    : indicators.rsi < 30
                      ? 'Oversold'
                      : 'Neutral'
                  : undefined
              }
              deltaType={
                indicators
                  ? indicators.rsi > 70
                    ? 'down'
                    : indicators.rsi < 30
                      ? 'up'
                      : 'neutral'
                  : 'neutral'
              }
              loading={indicatorsLoading}
            />
            <MetricCard
              label="MACD"
              value={indicators ? indicators.macd.value.toFixed(4) : '...'}
              delta={
                indicators
                  ? indicators.macd.histogram > 0
                    ? 'Bullish'
                    : 'Bearish'
                  : undefined
              }
              deltaType={
                indicators
                  ? indicators.macd.histogram > 0
                    ? 'up'
                    : 'down'
                  : 'neutral'
              }
              loading={indicatorsLoading}
            />
            <MetricCard
              label="MA20"
              value={indicators ? `$${indicators.ma20.toFixed(2)}` : '...'}
              delta={
                indicators && stock
                  ? stock.price > indicators.ma20
                    ? 'Above'
                    : 'Below'
                  : undefined
              }
              deltaType={
                indicators && stock
                  ? stock.price > indicators.ma20
                    ? 'up'
                    : 'down'
                  : 'neutral'
              }
              loading={indicatorsLoading}
            />
            <MetricCard
              label="MA200"
              value={indicators ? `$${indicators.ma200.toFixed(2)}` : '...'}
              delta={
                indicators && stock
                  ? stock.price > indicators.ma200
                    ? 'Above'
                    : 'Below'
                  : undefined
              }
              deltaType={
                indicators && stock
                  ? stock.price > indicators.ma200
                    ? 'up'
                    : 'down'
                  : 'neutral'
              }
              loading={indicatorsLoading}
            />
          </div>
        </TabsContent>

        {/* Options Tab */}
        <TabsContent value="options" className="space-y-4">
          {options?.estimated && (
            <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
              ⚠️ 估算值 · 基于价格走势 · 非真实期权链
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <MetricCard
              label="Max Pain"
              value={options ? `$${options.maxPain.toFixed(2)}` : '...'}
              loading={optionsLoading}
            />
            <MetricCard
              label="Put/Call Ratio"
              value={options ? options.putCallRatio.toFixed(2) : '...'}
              delta={
                options
                  ? options.putCallRatio > 1
                    ? 'Bearish'
                    : 'Bullish'
                  : undefined
              }
              deltaType={
                options
                  ? options.putCallRatio > 1
                    ? 'down'
                    : 'up'
                  : 'neutral'
              }
              loading={optionsLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-success">Support Levels</CardTitle>
              </CardHeader>
              <CardContent>
                {options?.support?.length ? (
                  <div className="space-y-2">
                    {options.support.map((level, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between rounded-md bg-success/5 p-2"
                      >
                        <span className="text-sm text-muted-foreground">
                          Level {index + 1}
                        </span>
                        <span className="font-mono font-medium tabular-nums text-success">
                          ${level.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No support levels available</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-error">Resistance Levels</CardTitle>
              </CardHeader>
              <CardContent>
                {options?.resistance?.length ? (
                  <div className="space-y-2">
                    {options.resistance.map((level, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between rounded-md bg-error/5 p-2"
                      >
                        <span className="text-sm text-muted-foreground">
                          Level {index + 1}
                        </span>
                        <span className="font-mono font-medium tabular-nums text-error">
                          ${level.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No resistance levels available</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Signals Tab */}
        <TabsContent value="signals" className="space-y-4">
          {signals ? (
            <SignalCard
              signalType={signals.type}
              score={signals.score}
              probability={signals.probability}
              reasons={signals.reasons}
              loading={signalsLoading}
            />
          ) : (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                Loading signals...
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <CardTitle>Signal History</CardTitle>
                <HelpTooltip helpKey="analysis.signalHistory" />
              </div>
            </CardHeader>
            <CardContent>
              {signalHistory && signalHistory.length > 0 ? (
                <SignalHistoryChart data={signalHistory} height={350} />
              ) : (
                <div className="flex h-[350px] items-center justify-center text-sm text-muted-foreground">
                  No signal history available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Risk Tab */}
        <TabsContent value="risk" className="space-y-4">
          {risk ? (
            <StatusCard
              title="OFF Filter Status"
              status={risk.statusText}
              isGood={risk.status === 'on'}
              details={
                risk.reasons?.length
                  ? `Reasons: ${risk.reasons.join(', ')}`
                  : undefined
              }
              loading={riskLoading}
            />
          ) : (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                Loading risk assessment...
              </CardContent>
            </Card>
          )}

          {risk && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <MetricCard
                label="ON Percentage"
                value={`${risk.onPercent.toFixed(1)}%`}
                loading={riskLoading}
              />
              <MetricCard
                label="OFF Percentage"
                value={`${risk.offPercent.toFixed(1)}%`}
                loading={riskLoading}
              />
            </div>
          )}
        </TabsContent>

        {/* Multi-Timeframe Tab */}
        <TabsContent value="multi-tf" className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <CardTitle>Multi-Timeframe Analysis</CardTitle>
                <HelpTooltip helpKey="analysis.multiTimeframe" />
              </div>
            </CardHeader>
            <CardContent>
              <MultiTimeframeChart
                symbol={symbol}
                timeframes={[
                  { label: '1 Week', period: '1w', candles: candles1w, isLoading: !candles1w },
                  { label: '1 Month', period: '1m', candles: candles1m, isLoading: !candles1m },
                  { label: '3 Months', period: '3m', candles: candles3m, isLoading: !candles3m },
                  { label: '6 Months', period: '6m', candles: candles6m, isLoading: !candles6m },
                ]}
                activeIndicators={activeIndicators}
                height={300}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
