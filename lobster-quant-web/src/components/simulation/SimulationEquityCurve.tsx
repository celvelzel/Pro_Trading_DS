'use client'

import { useEffect, useRef, memo } from 'react'
import { useTheme } from 'next-themes'
import { createChart, ColorType, IChartApi, LineSeries } from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { PerformanceChartData } from '@/hooks/useSimulation'

interface SimulationEquityCurveProps {
  data: PerformanceChartData
  height?: number
}

/**
 * SimulationEquityCurve - Equity curve chart with benchmark overlay.
 *
 * Shows the strategy's portfolio value over time alongside a SPY benchmark,
 * both normalized to the same initial value.
 */
export const SimulationEquityCurve = memo(function SimulationEquityCurve({
  data,
  height = 400,
}: SimulationEquityCurveProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const { resolvedTheme } = useTheme()

  const strategyReturn = data.initialValue > 0
    ? ((data.finalValue - data.initialValue) / data.initialValue * 100)
    : 0
  const benchmarkReturn = data.initialValue > 0
    ? ((data.benchmarkFinalValue - data.initialValue) / data.initialValue * 100)
    : 0
  const alpha = strategyReturn - benchmarkReturn

  useEffect(() => {
    const container = chartContainerRef.current
    if (!container || data.strategyCurve.length === 0) return

    // Resolve Quant Terminal tokens from CSS variables so the chart
    // adapts to both light and dark themes without hardcoded colors.
    const css = getComputedStyle(container)
    const token = (name: string) => css.getPropertyValue(name).trim()
    const strategyColor = token('--chart-1')
    const benchmarkColor = token('--chart-3')
    const textColor = token('--muted-foreground')
    const gridColor = token('--border')

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor,
        fontSize: 12,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          labelBackgroundColor: strategyColor,
        },
        horzLine: {
          labelBackgroundColor: strategyColor,
        },
      },
      rightPriceScale: {
        borderColor: gridColor,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: gridColor,
        timeVisible: false,
        secondsVisible: false,
      },
    })

    // Strategy line (primary accent)
    const strategySeries = chart.addSeries(LineSeries, {
      color: strategyColor,
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBackgroundColor: strategyColor,
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineColor: strategyColor,
      priceLineWidth: 1,
      priceLineStyle: 2,
    })

    strategySeries.setData(
      data.strategyCurve.map((d) => ({
        time: d.date,
        value: d.value,
      }))
    )

    // Benchmark line (secondary)
    const benchmarkSeries = chart.addSeries(LineSeries, {
      color: benchmarkColor,
      lineWidth: 1,
      lineStyle: 0,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 3,
      crosshairMarkerBackgroundColor: benchmarkColor,
      lastValueVisible: true,
      priceLineVisible: false,
    })

    benchmarkSeries.setData(
      data.benchmarkCurve.map((d) => ({
        time: d.date,
        value: d.value,
      }))
    )

    chart.timeScale().fitContent()
    chartRef.current = chart

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        chart.applyOptions({ width })
      }
    })
    resizeObserver.observe(container)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [data, height, resolvedTheme])

  if (data.strategyCurve.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            style={{ height }}
            className="flex items-center justify-center text-muted-foreground"
          >
            No equity data available. Run a simulation to see results.
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <CardTitle className="flex items-center gap-2">
            Equity Curve
            <Badge variant={alpha >= 0 ? 'success' : 'destructive'}>
              {alpha >= 0 ? '+' : ''}{alpha.toFixed(1)}% alpha
            </Badge>
          </CardTitle>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 rounded bg-chart-1" />
              <span className="text-muted-foreground">Strategy ({strategyReturn >= 0 ? '+' : ''}{strategyReturn.toFixed(1)}%)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 rounded bg-chart-3" />
              <span className="text-muted-foreground">{data.benchmarkSymbol} ({benchmarkReturn >= 0 ? '+' : ''}{benchmarkReturn.toFixed(1)}%)</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div ref={chartContainerRef} />
      </CardContent>
    </Card>
  )
})
