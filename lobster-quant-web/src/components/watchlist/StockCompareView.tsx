'use client'

import { memo, useEffect, useRef } from 'react'
import { createChart, ColorType, LineSeries, type IChartApi, type UTCTimestamp } from 'lightweight-charts'
import { Button } from '@/components/ui/button'
import { X } from 'lucide-react'

interface CompareData {
  symbol: string
  data: { time: number; value: number }[]
}

interface StockCompareViewProps {
  symbols: string[]
  data?: CompareData[]
  onClose: () => void
  className?: string
}

const COLORS = ['#4285F4', '#34A853', '#EA4335', '#FBBC04', '#8AB4F8']

export const StockCompareView = memo(function StockCompareView({
  symbols,
  data = [],
  onClose,
  className,
}: StockCompareViewProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9aa0a6',
      },
      grid: {
        vertLines: { color: '#3c4043' },
        horzLines: { color: '#3c4043' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    // Add a line series for each stock
    data.forEach((stock, index) => {
      const series = chart.addSeries(LineSeries, {
        color: COLORS[index % COLORS.length],
        lineWidth: 2,
        title: stock.symbol,
      })

      // Normalize data to percentage change from first value
      if (stock.data.length > 0) {
        const firstValue = stock.data[0].value
        const normalizedData = stock.data.map((d) => ({
          time: d.time as UTCTimestamp,
          value: ((d.value - firstValue) / firstValue) * 100,
        }))
        series.setData(normalizedData)
      }
    })

    chart.timeScale().fitContent()

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [data])

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-text-primary">
            Stock Comparison
          </h3>
          <div className="flex items-center gap-3">
            {symbols.map((symbol, index) => (
              <div key={symbol} className="flex items-center gap-1">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="text-sm font-medium text-text-primary">
                  {symbol}
                </span>
              </div>
            ))}
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  )
})
