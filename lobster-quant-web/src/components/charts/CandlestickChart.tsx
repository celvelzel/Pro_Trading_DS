'use client'

import { useEffect, useRef, memo, useMemo } from 'react'
import { useTheme } from 'next-themes'
import { createChart, IChartApi, CandlestickSeries, HistogramSeries, LineSeries, type UTCTimestamp } from 'lightweight-charts'
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
 */
export const CandlestickChart = memo(function CandlestickChart({
  data,
  height = 400,
  showVolume = true,
  activeIndicators = [],
  className,
}: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  // Theme-aware colors
  const chartColors = useMemo(() => ({
    background: isDark ? '#0a0a0a' : '#FFFFFF',
    text: isDark ? '#e0e0e0' : '#202124',
    grid: isDark ? '#1a1a1a' : '#F0F0F0',
    border: isDark ? '#333333' : '#F0F0F0',
    upColor: '#34A853',
    downColor: '#EA4335',
    volumeUp: isDark ? 'rgba(52, 168, 83, 0.3)' : 'rgba(52, 168, 83, 0.5)',
    volumeDown: isDark ? 'rgba(234, 67, 53, 0.3)' : 'rgba(234, 67, 53, 0.5)',
  }), [isDark])

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: chartColors.background },
        textColor: chartColors.text,
      },
      grid: {
        vertLines: { color: chartColors.grid },
        horzLines: { color: chartColors.grid },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: chartColors.border,
      },
      timeScale: {
        borderColor: chartColors.border,
        timeVisible: true,
        secondsVisible: false,
      },
    })

    // Add candlestick series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: chartColors.upColor,
      downColor: chartColors.downColor,
      borderDownColor: chartColors.downColor,
      borderUpColor: chartColors.upColor,
      wickDownColor: chartColors.downColor,
      wickUpColor: chartColors.upColor,
    })

    // Set candlestick data
    candlestickSeries.setData(
      data.map((d) => ({
        time: d.time as UTCTimestamp,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    )

    // Add volume series if enabled
    if (showVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: chartColors.volumeUp,
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
          time: d.time as UTCTimestamp,
          value: d.volume,
          color: d.close >= d.open ? chartColors.volumeUp : chartColors.volumeDown,
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
          .setData(formatIndicatorData(data, sma20))
        chart.addSeries(LineSeries, { color: '#4CAF50', lineWidth: 1 })
          .setData(formatIndicatorData(data, sma50))
        chart.addSeries(LineSeries, { color: '#F44336', lineWidth: 1 })
          .setData(formatIndicatorData(data, sma200))
      }

      // EMA overlays
      if (activeIndicators.includes('ema')) {
        const ema12 = calculateEMA(closePrices, 12)
        const ema26 = calculateEMA(closePrices, 26)

        chart.addSeries(LineSeries, { color: '#FF9800', lineWidth: 1 })
          .setData(formatIndicatorData(data, ema12))
        chart.addSeries(LineSeries, { color: '#9C27B0', lineWidth: 1 })
          .setData(formatIndicatorData(data, ema26))
      }

      // Bollinger Bands overlays
      if (activeIndicators.includes('bb')) {
        const bbData = calculateBollingerBands(closePrices, 20, 2)
        const upper = bbData.map(d => d.upper)
        const middle = bbData.map(d => d.middle)
        const lower = bbData.map(d => d.lower)
        
        chart.addSeries(LineSeries, { color: '#607D8B', lineWidth: 1 })
          .setData(formatIndicatorData(data, upper))
        chart.addSeries(LineSeries, { color: '#607D8B80', lineWidth: 1 })
          .setData(formatIndicatorData(data, lower))
        chart.addSeries(LineSeries, { color: '#607D8B40', lineWidth: 1 })
          .setData(formatIndicatorData(data, middle))
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
  }, [data, height, showVolume, activeIndicators, isDark, chartColors])

  const showRSI = activeIndicators.includes('rsi')
  const showMACD = activeIndicators.includes('macd')

  return (
    <div className={className}>
      <div
        ref={chartContainerRef}
        style={{ width: '100%', height: `${height}px` }}
      />
      {showRSI && (
        <div className="mt-1 px-1">
          <p className="text-xs text-text-tertiary">RSI (14)</p>
        </div>
      )}
      {showMACD && (
        <div className="mt-1 px-1">
          <p className="text-xs text-text-tertiary">MACD (12, 26, 9)</p>
        </div>
      )}
    </div>
  )
})
