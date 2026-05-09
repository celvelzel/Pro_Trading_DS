'use client'

import { useStockData, useStockRisk } from '@/hooks/useStock'
import { MetricCard } from '@/components/cards/MetricCard'
import { StatusCard } from '@/components/cards/StatusCard'
import { CandlestickChart } from '@/components/charts/CandlestickChart'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function DashboardPage() {
  // Fetch benchmark data (SPY)
  const { data: benchmark, isLoading: benchmarkLoading } = useStockData('SPY')
  const { data: risk, isLoading: riskLoading } = useStockRisk('SPY')

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
              {benchmarkLoading ? 'Loading chart data...' : 'No data available'}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Volume"
          value={
            benchmark?.volume
              ? `${(benchmark.volume / 1000000).toFixed(1)}M`
              : '...'
          }
          loading={benchmarkLoading}
        />
        <MetricCard
          label="Day Range"
          value={
            benchmark?.candles?.length
              ? `$${Math.min(...benchmark.candles.slice(-1).map((c) => c.low)).toFixed(2)} - $${Math.max(...benchmark.candles.slice(-1).map((c) => c.high)).toFixed(2)}`
              : '...'
          }
          loading={benchmarkLoading}
        />
        <MetricCard
          label="52W High"
          value={
            benchmark?.candles?.length
              ? `$${Math.max(...benchmark.candles.map((c) => c.high)).toFixed(2)}`
              : '...'
          }
          loading={benchmarkLoading}
        />
        <MetricCard
          label="52W Low"
          value={
            benchmark?.candles?.length
              ? `$${Math.min(...benchmark.candles.map((c) => c.low)).toFixed(2)}`
              : '...'
          }
          loading={benchmarkLoading}
        />
      </div>
    </div>
  )
}
