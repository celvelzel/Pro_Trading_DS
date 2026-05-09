'use client'

import { useState } from 'react'
import { useRunBacktest } from '@/hooks/useStock'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MetricCard } from '@/components/cards/MetricCard'
import { FlaskConical, Play } from 'lucide-react'

export default function BacktestPage() {
  const [symbol, setSymbol] = useState('SPY')
  const [holdingDays, setHoldingDays] = useState(10)
  const [minScore, setMinScore] = useState(60)
  const backtestMutation = useRunBacktest()

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault()
    backtestMutation.mutate({
      symbol: symbol.toUpperCase(),
      holdingDays,
      minScore,
    })
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Strategy Backtest</h1>
        <p className="text-text-secondary mt-1">
          Test your trading strategy with historical data
        </p>
      </div>

      {/* Backtest Parameters */}
      <Card>
        <CardHeader>
          <CardTitle>Backtest Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRun} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Symbol Input */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Stock Symbol
                </label>
                <Input
                  type="text"
                  placeholder="e.g., SPY, AAPL"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  required
                />
              </div>

              {/* Holding Days */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Holding Days: {holdingDays}
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
              </div>

              {/* Min Score */}
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Minimum Score: {minScore}
                </label>
                <Slider
                  value={[minScore]}
                  onValueChange={(value) => {
                    const val = Array.isArray(value) ? value[0] : value
                    setMinScore(val)
                  }}
                  min={0}
                  max={100}
                  step={5}
                  className="mt-2"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={backtestMutation.isPending}
              className="w-full md:w-auto"
            >
              {backtestMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Running Backtest...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run Backtest
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error Message */}
      {backtestMutation.isError && (
        <Card className="border-error">
          <CardContent className="p-4">
            <p className="text-error">
              Error: {backtestMutation.error?.message || 'Failed to run backtest'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {backtestMutation.data && (
        <div className="space-y-4">
          {/* Summary Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Total Trades"
              value={backtestMutation.data.totalTrades.toString()}
            />
            <MetricCard
              label="Win Rate"
              value={`${backtestMutation.data.winRate.toFixed(1)}%`}
              deltaType={
                backtestMutation.data.winRate >= 50 ? 'up' : 'down'
              }
            />
            <MetricCard
              label="Total Return"
              value={`${backtestMutation.data.totalReturn.toFixed(2)}%`}
              deltaType={
                backtestMutation.data.totalReturn >= 0 ? 'up' : 'down'
              }
            />
            <MetricCard
              label="Max Drawdown"
              value={`${backtestMutation.data.maxDrawdown.toFixed(2)}%`}
              deltaType="down"
            />
          </div>

          {/* Additional Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MetricCard
              label="Sharpe Ratio"
              value={backtestMutation.data.sharpeRatio.toFixed(2)}
              deltaType={
                backtestMutation.data.sharpeRatio >= 1
                  ? 'up'
                  : backtestMutation.data.sharpeRatio >= 0
                    ? 'neutral'
                    : 'down'
              }
            />
            <MetricCard
              label="Avg Holding Days"
              value={holdingDays.toString()}
            />
          </div>

          {/* Trades Table */}
          <Card>
            <CardHeader>
              <CardTitle>Trade History</CardTitle>
            </CardHeader>
            <CardContent>
              {backtestMutation.data.trades.length === 0 ? (
                <p className="text-text-secondary text-center py-8">
                  No trades were executed during the backtest period
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                          Entry Date
                        </th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                          Exit Date
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                          Entry Price
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                          Exit Price
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                          Return
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                          Days
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {backtestMutation.data.trades.slice(0, 20).map((trade, index) => (
                        <tr
                          key={index}
                          className="border-b border-gray-100 hover:bg-bg-hover"
                        >
                          <td className="py-3 px-4 text-sm">
                            {trade.entryDate}
                          </td>
                          <td className="py-3 px-4 text-sm">
                            {trade.exitDate}
                          </td>
                          <td className="py-3 px-4 text-sm text-right">
                            ${trade.entryPrice.toFixed(2)}
                          </td>
                          <td className="py-3 px-4 text-sm text-right">
                            ${trade.exitPrice.toFixed(2)}
                          </td>
                          <td
                            className={`py-3 px-4 text-sm text-right font-medium ${
                              trade.returnPercent >= 0
                                ? 'text-success'
                                : 'text-error'
                            }`}
                          >
                            {trade.returnPercent >= 0 ? '+' : ''}
                            {trade.returnPercent.toFixed(2)}%
                          </td>
                          <td className="py-3 px-4 text-sm text-right">
                            {trade.holdingDays}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {backtestMutation.data.trades.length > 20 && (
                    <p className="text-text-secondary text-center py-4 text-sm">
                      Showing first 20 of {backtestMutation.data.trades.length} trades
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
