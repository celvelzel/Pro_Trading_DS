'use client'

import { memo, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { Candle } from '@/lib/types'

interface TimeframeInfo {
  label: string
  period: string
  candles: Candle[] | undefined
}

interface TimeframeSummaryProps {
  timeframes: TimeframeInfo[]
}

interface TrendInfo {
  direction: 'up' | 'down' | 'neutral'
  change: number
  rsi: number | null
}

function calculateTrend(candles: Candle[] | undefined): TrendInfo {
  if (!candles || candles.length < 2) {
    return { direction: 'neutral', change: 0, rsi: null }
  }

  const first = candles[0].close
  const last = candles[candles.length - 1].close
  const change = ((last - first) / first) * 100

  // Simple RSI calculation (14-period)
  let rsi: number | null = null
  if (candles.length >= 15) {
    const changes = []
    for (let i = 1; i < candles.length; i++) {
      changes.push(candles[i].close - candles[i - 1].close)
    }

    const recentChanges = changes.slice(-14)
    let gains = 0
    let losses = 0

    for (const change of recentChanges) {
      if (change > 0) gains += change
      else losses += Math.abs(change)
    }

    const avgGain = gains / 14
    const avgLoss = losses / 14

    if (avgLoss === 0) {
      rsi = 100
    } else {
      const rs = avgGain / avgLoss
      rsi = 100 - (100 / (1 + rs))
    }
  }

  return {
    direction: change > 0.5 ? 'up' : change < -0.5 ? 'down' : 'neutral',
    change,
    rsi,
  }
}

export const TimeframeSummary = memo(function TimeframeSummary({
  timeframes,
}: TimeframeSummaryProps) {
  const trends = useMemo(() => {
    return timeframes.map((tf) => ({
      label: tf.label,
      ...calculateTrend(tf.candles),
    }))
  }, [timeframes])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Timeframe Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {trends.map((trend) => (
            <div
              key={trend.label}
              className="flex flex-col items-center p-3 rounded-lg border"
            >
              <span className="text-sm font-medium text-text-secondary mb-2">
                {trend.label}
              </span>
              <div className="flex items-center gap-2 mb-1">
                {trend.direction === 'up' ? (
                  <TrendingUp className="w-4 h-4 text-success" />
                ) : trend.direction === 'down' ? (
                  <TrendingDown className="w-4 h-4 text-error" />
                ) : (
                  <Minus className="w-4 h-4 text-text-secondary" />
                )}
                <span
                  className={`font-semibold ${
                    trend.direction === 'up'
                      ? 'text-success'
                      : trend.direction === 'down'
                        ? 'text-error'
                        : 'text-text-secondary'
                  }`}
                >
                  {trend.change >= 0 ? '+' : ''}
                  {trend.change.toFixed(1)}%
                </span>
              </div>
              {trend.rsi !== null && (
                <span className="text-xs text-text-secondary">
                  RSI {trend.rsi.toFixed(0)}
                </span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
})
