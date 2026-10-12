'use client'

import { memo, useEffect, useRef, useState } from 'react'
import { createChart, ColorType, LineSeries, type IChartApi, type UTCTimestamp } from 'lightweight-charts'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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

// Series palette sourced from theme tokens (fallbacks mirror globals.css)
const COLOR_VARS = [
  '--color-primary',
  '--color-success',
  '--color-error',
  '--color-warning',
  '--chart-4',
]
const FALLBACK_COLORS = ['#3E7BFA', '#22C55E', '#EF4444', '#D97706', '#A855F7']

function themeColors(): string[] {
  if (typeof window === 'undefined') return FALLBACK_COLORS
  const styles = getComputedStyle(document.documentElement)
  return COLOR_VARS.map(
    (name, i) => styles.getPropertyValue(name).trim() || FALLBACK_COLORS[i]
  )
}

function themeVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export const StockCompareView = memo(function StockCompareView({
  symbols,
  data = [],
  onClose,
  className,
}: StockCompareViewProps) {
  const { resolvedTheme } = useTheme()
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [colors, setColors] = useState<string[]>(FALLBACK_COLORS)

  // Resolve palette from the active theme once mounted
  useEffect(() => {
    setColors(themeColors())
  }, [resolvedTheme])

  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: themeVar('--muted-foreground', '#8B95A5'),
      },
      grid: {
        vertLines: { color: themeVar('--border', 'rgba(139, 149, 165, 0.15)') },
        horzLines: { color: themeVar('--border', 'rgba(139, 149, 165, 0.15)') },
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
        color: colors[index % colors.length],
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
  }, [data, colors])

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span>Stock Comparison</span>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {symbols.map((symbol, index) => {
              const series = data.find((d) => d.symbol === symbol)
              const first = series?.data[0]?.value
              const last =
                series && series.data.length > 0
                  ? series.data[series.data.length - 1].value
                  : undefined
              const pct =
                first !== undefined && first !== 0 && last !== undefined
                  ? ((last - first) / first) * 100
                  : undefined
              return (
                <div key={symbol} className="flex items-center gap-1.5">
                  <span
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: colors[index % colors.length] }}
                  />
                  <span className="font-mono text-sm font-medium text-foreground">
                    {symbol}
                  </span>
                  {pct !== undefined && (
                    <span
                      className={cn(
                        'font-mono text-xs font-medium tabular-nums',
                        pct >= 0 ? 'text-success' : 'text-error'
                      )}
                    >
                      {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </CardTitle>
        <CardAction>
          <Button variant="ghost" size="icon-sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        <div ref={chartContainerRef} className="w-full" />
      </CardContent>
    </Card>
  )
})
