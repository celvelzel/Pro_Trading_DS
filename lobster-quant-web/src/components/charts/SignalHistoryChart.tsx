'use client'

import { useEffect, useRef, memo } from 'react'
import { useTheme } from 'next-themes'
import { createChart, IChartApi, LineSeries, createSeriesMarkers, type UTCTimestamp } from 'lightweight-charts'
import { chartTheme } from '@/lib/chart-theme'
import type { SignalHistoryEntry } from '@/lib/types'

interface SignalHistoryChartProps {
  data: SignalHistoryEntry[]
  height?: number
  className?: string
}

/**
 * SignalHistoryChart - Renders a line chart of signal score over time.
 *
 * Uses Lightweight Charts LineSeries for a clean visualization.
 * Colors the line based on signal type (bullish/bearish/neutral).
 * Memoized to prevent unnecessary chart rebuilds on parent re-renders.
 */
export const SignalHistoryChart = memo(function SignalHistoryChart({
  data,
  height = 400,
  className,
}: SignalHistoryChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const { resolvedTheme } = useTheme()

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return

    const chartColors = chartTheme()
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: chartColors.background },
        textColor: chartColors.text,
        fontSize: 12,
      },
      grid: {
        vertLines: { color: chartColors.grid },
        horzLines: { color: chartColors.grid },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          labelBackgroundColor: chartColors.neutral,
        },
        horzLine: {
          labelBackgroundColor: chartColors.neutral,
        },
      },
      rightPriceScale: {
        borderColor: chartColors.grid,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: chartColors.grid,
        timeVisible: false,
        secondsVisible: false,
      },
    })

    const lineSeries = chart.addSeries(LineSeries, {
      color: chartColors.neutral,
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBackgroundColor: chartColors.neutral,
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineColor: chartColors.neutral,
      priceLineWidth: 1,
      priceLineStyle: 2,
    })

    // Sort data by date ascending for chart
    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date))

    lineSeries.setData(
      sortedData.map((d) => ({
        time: d.date as unknown as UTCTimestamp,
        value: d.score,
      }))
    )

    // Add markers for signal type changes
    const markers = sortedData
      .filter((entry, index) => {
        if (index === 0) return true
        return entry.signalType !== sortedData[index - 1].signalType
      })
      .map((entry) => ({
        time: entry.date as unknown as UTCTimestamp,
        position: 'belowBar' as const,
        color: entry.signalType === 'bullish'
          ? chartColors.bullish
          : entry.signalType === 'bearish'
            ? chartColors.bearish
            : chartColors.neutral,
        shape: entry.signalType === 'bullish'
          ? 'arrowUp' as const
          : entry.signalType === 'bearish'
            ? 'arrowDown' as const
            : 'circle' as const,
        text: entry.signalType,
      }))

    if (markers.length > 0) {
      createSeriesMarkers(lineSeries, markers)
    }

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
        className={`flex items-center justify-center text-muted-foreground ${className ?? ''}`}
        style={{ height }}
      >
        No signal history available
      </div>
    )
  }

  return <div ref={chartContainerRef} className={className} />
})
