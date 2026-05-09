'use client'

import { useState } from 'react'
import { useScanStocks } from '@/hooks/useStock'
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
import { MetricCard } from '@/components/cards/MetricCard'
import { SignalCard } from '@/components/cards/SignalCard'
import { Search } from 'lucide-react'
import type { Market } from '@/lib/types'

export default function ScannerPage() {
  const [market, setMarket] = useState<Market>('US')
  const [minScore, setMinScore] = useState(60)
  const scanMutation = useScanStocks()

  const handleScan = () => {
    scanMutation.mutate({ market, minScore })
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Stock Scanner</h1>
        <p className="text-text-secondary mt-1">
          Scan stocks across multiple markets based on technical criteria
        </p>
      </div>

      {/* Scan Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Scan Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            {/* Market Selection */}
            <div className="flex-1">
              <label className="text-sm font-medium text-text-secondary mb-2 block">
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
            <div className="flex-1">
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Minimum Score: {minScore}
              </label>
              <Slider
                value={[minScore]}
                onValueChange={(value) => {
                  const val = Array.isArray(value) ? value[0] : value
                  setMinScore(val)
                }}
                max={100}
                min={0}
                step={5}
                className="mt-2"
              />
            </div>

            {/* Scan Button */}
            <div className="flex items-end">
              <Button
                onClick={handleScan}
                disabled={scanMutation.isPending}
                className="w-full md:w-auto"
              >
                {scanMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4 mr-2" />
                    Scan Stocks
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {scanMutation.isError && (
        <Card className="border-error">
          <CardContent className="p-4">
            <p className="text-error">
              Error: {scanMutation.error?.message || 'Failed to scan stocks'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {scanMutation.data && (
        <div className="space-y-4">
          {/* Results Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard
              label="Stocks Found"
              value={scanMutation.data.total.toString()}
            />
            <MetricCard
              label="Market"
              value={scanMutation.data.market}
            />
            <MetricCard
              label="Min Score"
              value={scanMutation.data.minScore.toString()}
            />
          </div>

          {/* Results Table */}
          <Card>
            <CardHeader>
              <CardTitle>Scan Results</CardTitle>
            </CardHeader>
            <CardContent>
              {scanMutation.data.results.length === 0 ? (
                <p className="text-text-secondary text-center py-8">
                  No stocks found matching your criteria
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                          Symbol
                        </th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                          Name
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                          Price
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                          Change
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                          Score
                        </th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                          Signal
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {scanMutation.data.results.map((stock) => (
                        <tr
                          key={stock.symbol}
                          className="border-b border-gray-100 hover:bg-bg-hover"
                        >
                          <td className="py-3 px-4">
                            <a
                              href={`/analysis/${stock.symbol}`}
                              className="font-medium text-primary hover:underline"
                            >
                              {stock.symbol}
                            </a>
                          </td>
                          <td className="py-3 px-4 text-text-secondary">
                            {stock.name}
                          </td>
                          <td className="py-3 px-4 text-right font-medium">
                            ${stock.price.toFixed(2)}
                          </td>
                          <td
                            className={`py-3 px-4 text-right font-medium ${
                              stock.change >= 0 ? 'text-success' : 'text-error'
                            }`}
                          >
                            {stock.change >= 0 ? '+' : ''}
                            {stock.change.toFixed(2)} ({stock.changePercent.toFixed(2)}%)
                          </td>
                          <td className="py-3 px-4 text-right font-medium">
                            {stock.score}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                stock.signalType === 'bullish'
                                  ? 'bg-success/10 text-success'
                                  : stock.signalType === 'bearish'
                                    ? 'bg-error/10 text-error'
                                    : 'bg-warning/10 text-warning'
                              }`}
                            >
                              {stock.signalType === 'bullish'
                                ? '🟢 Bullish'
                                : stock.signalType === 'bearish'
                                  ? '🔴 Bearish'
                                  : '🟡 Neutral'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Detailed Results */}
          {scanMutation.data.results.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {scanMutation.data.results.slice(0, 6).map((stock) => (
                <SignalCard
                  key={stock.symbol}
                  signalType={stock.signalType}
                  score={stock.score}
                  probability={0}
                  reasons={stock.reasons}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
