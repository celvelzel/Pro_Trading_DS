'use client'

import { useEffect, useRef, memo } from 'react'
import { createChart, IChartApi, LineSeries } from 'lightweight-charts'
import { useTheme } from 'next-themes'
import { chartTheme } from '@/lib/chart-theme'
import type { EquityPoint } from '@/lib/types'

interface EquityCurveChartProps {
  data: EquityPoint[]
  height?: number
  className?: string
}

/**
 * EquityCurveChart - Renders a line chart of portfolio equity over time.
 *
 * Uses Lightweight Charts LineSeries for a clean Google Finance-style look.
 * Memoized to prevent unnecessary chart rebuilds on parent re-renders.
 */
export const EquityCurveChart = memo(function EquityCurveChart({
  data,
  height = 400,
  className,
}: EquityCurveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  const { resolvedTheme } = useTheme()

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return

    const colors = chartTheme()
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: colors.background },
        textColor: colors.text,
        fontSize: 12,
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          labelBackgroundColor: colors.primary,
        },
        horzLine: {
          labelBackgroundColor: colors.primary,
        },
      },
      rightPriceScale: {
        borderColor: colors.grid,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: colors.grid,
        timeVisible: false,
        secondsVisible: false,
      },
    })

    const lineSeries = chart.addSeries(LineSeries, {
      color: colors.primary,
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBackgroundColor: colors.primary,
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineColor: colors.primary,
      priceLineWidth: 1,
      priceLineStyle: 2,
    })

    lineSeries.setData(
      data.map((d) => ({
        time: d.date,
        value: d.value,
      }))
    )

    chart.timeScale().fitContent()
    chartRef.current = chart

    // Resize observer for responsive width
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        chart.applyOptions({ width })
      }
    })
    resizeObserver.observe(chartContainerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [data, height, resolvedTheme])

  if (data.length === 0) {
    return (
      <div
        className={className}
        style={{ height }}
      >
        <div className="flex items-center justify-center h-full text-muted-foreground">
          No equity data available
        </div>
      </div>
    )
  }

  return <div ref={chartContainerRef} className={className} />
})
