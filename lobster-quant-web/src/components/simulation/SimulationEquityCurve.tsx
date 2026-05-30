'use client'

import { useEffect, useRef, memo } from 'react'
import { createChart, IChartApi, LineSeries } from 'lightweight-charts'
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

  const strategyReturn = data.initialValue > 0
    ? ((data.finalValue - data.initialValue) / data.initialValue * 100)
    : 0
  const benchmarkReturn = data.initialValue > 0
    ? ((data.benchmarkFinalValue - data.initialValue) / data.initialValue * 100)
    : 0
  const alpha = strategyReturn - benchmarkReturn

  useEffect(() => {
    if (!chartContainerRef.current || data.strategyCurve.length === 0) return

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

    // Strategy line (primary - blue)
    const strategySeries = chart.addSeries(LineSeries, {
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

    strategySeries.setData(
      data.strategyCurve.map((d) => ({
        time: d.date,
        value: d.value,
      }))
    )

    // Benchmark line (secondary - grey/orange dashed feel via color)
    const benchmarkSeries = chart.addSeries(LineSeries, {
      color: '#F9AB00',
      lineWidth: 1,
      lineStyle: 0,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 3,
      crosshairMarkerBackgroundColor: '#F9AB00',
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
    resizeObserver.observe(chartContainerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [data, height])

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
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            Equity Curve
            <Badge variant={alpha >= 0 ? 'default' : 'destructive'}>
              {alpha >= 0 ? '+' : ''}{alpha.toFixed(1)}% alpha
            </Badge>
          </CardTitle>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-[#1A73E8] rounded" />
              <span className="text-muted-foreground">Strategy ({strategyReturn >= 0 ? '+' : ''}{strategyReturn.toFixed(1)}%)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-[#F9AB00] rounded" />
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
