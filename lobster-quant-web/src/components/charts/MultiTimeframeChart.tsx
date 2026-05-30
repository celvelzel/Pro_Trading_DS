'use client'

import { memo } from 'react'
import { CandlestickChart } from './CandlestickChart'
import { ChartSkeleton } from './ChartSkeleton'
import type { Candle } from '@/lib/types'
import type { IndicatorType } from './IndicatorToggle'

interface TimeframeData {
  label: string
  period: string
  candles: Candle[] | undefined
  isLoading: boolean
}

interface MultiTimeframeChartProps {
  symbol: string
  timeframes: TimeframeData[]
  activeIndicators?: IndicatorType[]
  height?: number
}

export const MultiTimeframeChart = memo(function MultiTimeframeChart({
  symbol,
  timeframes,
  activeIndicators = [],
  height = 300,
}: MultiTimeframeChartProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {timeframes.map((tf) => (
        <div key={tf.period} className="border rounded-lg overflow-hidden">
          <div className="px-3 py-2 bg-muted/50 border-b">
            <span className="text-sm font-medium">{tf.label}</span>
          </div>
          <div className="p-1">
            {tf.isLoading ? (
              <ChartSkeleton height={height} />
            ) : tf.candles && tf.candles.length > 0 ? (
              <CandlestickChart
                data={tf.candles}
                symbol={symbol}
                height={height}
                showVolume={false}
                activeIndicators={activeIndicators}
              />
            ) : (
              <div
                className="flex items-center justify-center text-text-secondary text-sm"
                style={{ height }}
              >
                No data available
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
})
