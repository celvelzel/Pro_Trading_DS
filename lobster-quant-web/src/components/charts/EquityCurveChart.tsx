'use client'

import { useEffect, useRef, memo } from 'react'
import { createChart, IChartApi, LineSeries } from 'lightweight-charts'
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

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: '#FFFFFF' },
        textColor: '#5F6368',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#F0F0F0' },
        horzLines: { color: '#F0F0F0' },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          labelBackgroundColor: '#1A73E8',
        },
        horzLine: {
          labelBackgroundColor: '#1A73E8',
        },
      },
      rightPriceScale: {
        borderColor: '#E8EAED',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#E8EAED',
        timeVisible: false,
        secondsVisible: false,
      },
    })

    const lineSeries = chart.addSeries(LineSeries, {
      color: '#1A73E8',
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBackgroundColor: '#1A73E8',
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineColor: '#1A73E8',
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
  }, [data, height])

  if (data.length === 0) {
    return (
      <div
        className={className}
        style={{ height }}
      >
        <div className="flex items-center justify-center h-full text-text-tertiary">
          No equity data available
        </div>
      </div>
    )
  }

  return <div ref={chartContainerRef} className={className} />
})
