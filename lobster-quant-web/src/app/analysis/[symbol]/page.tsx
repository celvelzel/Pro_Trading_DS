'use client'

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
      <div className="p-6 space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="h-4 bg-gray-200 rounded w-32" />
        </div>
        <ChartSkeleton height={400} />
      </div>
    )
  }

  // Error state
  if (!stock) {
    return (
      <div className="p-6">
        <Card className="border-error">
          <CardContent className="p-6 text-center">
            <p className="text-error text-lg">Failed to load data for {symbol}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Analysis', href: '/analysis' },
          { label: symbol },
        ]}
      />

      {/* Price Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold text-text-primary">
              {symbol}
            </h1>
            <HelpTooltip helpKey="analysis.title" />
          </div>
          <p className="text-text-secondary">{stock.name}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-3xl font-bold text-text-primary">
              ${stock.price.toFixed(2)}
            </p>
            <div
              className={`flex items-center gap-1 ${
                (stock.change ?? 0) >= 0 ? 'text-success' : 'text-error'
              }`}
            >
              {(stock.change ?? 0) >= 0 ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span className="font-medium">
                {(stock.change ?? 0) >= 0 ? '+' : ''}
                {(stock.change ?? 0).toFixed(2)} ({(stock.changePercent ?? 0).toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
            <BarChart3 className="w-4 h-4" />
            <span className="hidden md:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="technical" className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            <span className="hidden md:inline">Technical</span>
          </TabsTrigger>
          <TabsTrigger value="options" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span className="hidden md:inline">Options</span>
          </TabsTrigger>
          <TabsTrigger value="signals" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span className="hidden md:inline">Signals</span>
          </TabsTrigger>
          <TabsTrigger value="risk" className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            <span className="hidden md:inline">Risk</span>
          </TabsTrigger>
          <TabsTrigger value="multi-tf" className="flex items-center gap-2">
            <Layers className="w-4 h-4" />
            <span className="hidden md:inline">Multi-TF</span>
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
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
            <CardContent>
              {candles && candles.length > 0 ? (
                <AnnotatedCandlestickChart
                  data={candles}
                  symbol={symbol}
                  height={500}
                  showVolume={true}
                  activeIndicators={activeIndicators}
                />
              ) : (
                <div className="h-[400px] flex items-center justify-center text-text-secondary">
                  No chart data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Signal Summary & Score Decomposition */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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
            <div>
              <ScoreRadarChart 
                loading={signalsLoading}
                className="h-full"
              />
            </div>
          </div>
        </TabsContent>

        {/* Technical Tab */}
        <TabsContent value="technical" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 text-sm text-yellow-600 dark:text-yellow-400">
              ⚠️ 估算值 · 基于价格走势 · 非真实期权链
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-success">Support Levels</CardTitle>
              </CardHeader>
              <CardContent>
                {options?.support?.length ? (
                  <div className="space-y-2">
                    {options.support.map((level, index) => (
                      <div
                        key={index}
                        className="flex justify-between items-center p-2 bg-success/5 rounded"
                      >
                        <span className="text-text-secondary">Level {index + 1}</span>
                        <span className="font-medium text-success">
                          ${level.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-text-secondary">No support levels available</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-error">Resistance Levels</CardTitle>
              </CardHeader>
              <CardContent>
                {options?.resistance?.length ? (
                  <div className="space-y-2">
                    {options.resistance.map((level, index) => (
                      <div
                        key={index}
                        className="flex justify-between items-center p-2 bg-error/5 rounded"
                      >
                        <span className="text-text-secondary">Level {index + 1}</span>
                        <span className="font-medium text-error">
                          ${level.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-text-secondary">No resistance levels available</p>
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
              <CardContent className="p-6 text-center text-text-secondary">
                Loading signals...
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CardTitle>Signal History</CardTitle>
                <HelpTooltip helpKey="analysis.signalHistory" />
              </div>
            </CardHeader>
            <CardContent>
              {signalHistory && signalHistory.length > 0 ? (
                <SignalHistoryChart data={signalHistory} height={350} />
              ) : (
                <div className="h-[350px] flex items-center justify-center text-text-secondary text-sm">
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
              <CardContent className="p-6 text-center text-text-secondary">
                Loading risk assessment...
              </CardContent>
            </Card>
          )}

          {risk && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <CardHeader>
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
