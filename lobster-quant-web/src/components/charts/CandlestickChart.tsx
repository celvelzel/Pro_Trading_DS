'use client'

import { useEffect, useRef, memo } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts'
import type { Candle } from '@/lib/types'
import type { IndicatorType } from './IndicatorToggle'
import { calculateSMA, calculateEMA, calculateBollingerBands, getClosePrices, formatIndicatorData } from '@/lib/indicators'

interface CandlestickChartProps {
  data: Candle[]
  symbol: string
  height?: number
  showVolume?: boolean
  activeIndicators?: IndicatorType[]
  className?: string
}

/**
 * CandlestickChart - Memoized chart component for OHLCV data.
 *
 * WHY MEMOIZED: This component is expensive — it creates a Lightweight Charts
 * instance, sets up series, and renders potentially hundreds of candlesticks.
 * Without memo, every parent re-render (e.g., from unrelated state changes)
 * would destroy and recreate the entire chart DOM + canvas.
 *
 * The memo comparison checks `data` reference, `symbol`, `height`, and
 * `showVolume`. Since React Query returns stable references for cached data,
 * this prevents unnecessary chart rebuilds.
 */
export const CandlestickChart = memo(function CandlestickChart({
  data,
  symbol,
  height = 400,
  showVolume = true,
  activeIndicators = [],
  className,
}: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: '#FFFFFF' },
        textColor: '#202124',
      },
      grid: {
        vertLines: { color: '#F0F0F0' },
        horzLines: { color: '#F0F0F0' },
      },
      crosshair: {
        mode: 0, // Normal mode
      },
      rightPriceScale: {
        borderColor: '#F0F0F0',
      },
      timeScale: {
        borderColor: '#F0F0F0',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    // Add candlestick series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#34A853',
      downColor: '#EA4335',
      borderDownColor: '#EA4335',
      borderUpColor: '#34A853',
      wickDownColor: '#EA4335',
      wickUpColor: '#34A853',
    })

    // Set candlestick data
    candlestickSeries.setData(
      data.map((d) => ({
        time: d.time as any,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    )

    // Add volume series if enabled
    if (showVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: '#26a69a',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '',
      })

      volumeSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      })

      volumeSeries.setData(
        data.map((d) => ({
          time: d.time as any,
          value: d.volume,
          color: d.close >= d.open ? '#34A85380' : '#EA433580',
        }))
      )
    }

    // Add technical indicator overlays
    if (activeIndicators.length > 0) {
      const closePrices = getClosePrices(data)

      // SMA overlays
      if (activeIndicators.includes('sma')) {
        const sma20 = calculateSMA(closePrices, 20)
        const sma50 = calculateSMA(closePrices, 50)
        const sma200 = calculateSMA(closePrices, 200)

        chart.addSeries(LineSeries, { color: '#2196F3', lineWidth: 1 })
          .setData(formatIndicatorData(data, sma20) as any)
        chart.addSeries(LineSeries, { color: '#4CAF50', lineWidth: 1 })
          .setData(formatIndicatorData(data, sma50) as any)
        chart.addSeries(LineSeries, { color: '#F44336', lineWidth: 1 })
          .setData(formatIndicatorData(data, sma200) as any)
      }

      // EMA overlays
      if (activeIndicators.includes('ema')) {
        const ema12 = calculateEMA(closePrices, 12)
        const ema26 = calculateEMA(closePrices, 26)

        chart.addSeries(LineSeries, { color: '#FF9800', lineWidth: 1 })
          .setData(formatIndicatorData(data, ema12) as any)
        chart.addSeries(LineSeries, { color: '#9C27B0', lineWidth: 1 })
          .setData(formatIndicatorData(data, ema26) as any)
      }

      // Bollinger Bands overlays
      if (activeIndicators.includes('bb')) {
        const bb = calculateBollingerBands(closePrices, 20, 2)
        const bbUpper = bb.map(b => b.upper)
        const bbMiddle = bb.map(b => b.middle)
        const bbLower = bb.map(b => b.lower)

        chart.addSeries(LineSeries, { color: '#2196F380', lineWidth: 1 })
          .setData(formatIndicatorData(data, bbUpper) as any)
        chart.addSeries(LineSeries, { color: '#9E9E9E80', lineWidth: 1 })
          .setData(formatIndicatorData(data, bbMiddle) as any)
        chart.addSeries(LineSeries, { color: '#2196F380', lineWidth: 1 })
          .setData(formatIndicatorData(data, bbLower) as any)
      }
    }

    // Fit content
    chart.timeScale().fitContent()

    // Store chart reference
    chartRef.current = chart

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
    }
  }, [data, height, showVolume, activeIndicators])

  return (
    <div
      ref={chartContainerRef}
      className={className}
      style={{ width: '100%', height: `${height}px` }}
    />
  )
})
