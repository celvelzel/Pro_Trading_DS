'use client'

import { useEffect, useRef, memo } from 'react'
import { useTheme } from 'next-themes'
import { createChart, IChartApi, CandlestickSeries, HistogramSeries, LineSeries, type UTCTimestamp } from 'lightweight-charts'
import type { Candle } from '@/lib/types'
import type { IndicatorType } from './IndicatorToggle'
import { calculateSMA, calculateEMA, calculateBollingerBands, calculateRSI, calculateMACD, getClosePrices, formatIndicatorData } from '@/lib/indicators'

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
  const chartColors = {
    background: isDark ? '#0a0a0a' : '#FFFFFF',
    text: isDark ? '#e0e0e0' : '#202124',
    grid: isDark ? '#1a1a1a' : '#F0F0F0',
    border: isDark ? '#333333' : '#F0F0F0',
    upColor: '#34A853',
    downColor: '#EA4335',
    volumeUp: isDark ? 'rgba(52, 168, 83, 0.3)' : 'rgba(52, 168, 83, 0.5)',
    volumeDown: isDark ? 'rgba(234, 67, 53, 0.3)' : 'rgba(234, 67, 53, 0.5)',
  }

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
        mode: 0, // Normal mode
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

    // RSI sub-chart
    if (activeIndicators.includes('rsi') && chartContainerRef.current) {
      const rsiContainer = document.createElement('div')
      rsiContainer.style.width = '100%'
      rsiContainer.style.height = '120px'
      chartContainerRef.current.parentNode?.insertBefore(rsiContainer, chartContainerRef.current.nextSibling)

      const rsiChart = createChart(rsiContainer, {
        width: chartContainerRef.current.clientWidth,
        height: 120,
        layout: {
          background: { color: '#FFFFFF' },
          textColor: '#5F6368',
        },
        grid: {
          vertLines: { color: '#F0F0F0' },
          horzLines: { color: '#F0F0F0' },
        },
        timeScale: {
          visible: false,
        },
      })

      const rsiData = calculateRSI(getClosePrices(data), 14)
      const rsiSeries = rsiChart.addSeries(LineSeries, {
        color: '#9C27B0',
        lineWidth: 1,
      })
      rsiSeries.setData(formatIndicatorData(data, rsiData) as any)

      // Add RSI levels (30 and 70)
      const rsiLine30 = rsiSeries.createPriceLine({ price: 30, color: '#EA433580', lineWidth: 1, lineStyle: 2 })
      const rsiLine70 = rsiSeries.createPriceLine({ price: 70, color: '#EA433580', lineWidth: 1, lineStyle: 2 })

      rsiChart.timeScale().fitContent()
    }

    // MACD sub-chart
    if (activeIndicators.includes('macd') && chartContainerRef.current) {
      const macdContainer = document.createElement('div')
      macdContainer.style.width = '100%'
      macdContainer.style.height = '120px'
      chartContainerRef.current.parentNode?.insertBefore(macdContainer, chartContainerRef.current.nextSibling?.nextSibling || null)

      const macdChart = createChart(macdContainer, {
        width: chartContainerRef.current.clientWidth,
        height: 120,
        layout: {
          background: { color: chartColors.background },
          textColor: chartColors.text,
        },
        grid: {
          vertLines: { color: chartColors.grid },
          horzLines: { color: chartColors.grid },
        },
        timeScale: {
          visible: false,
        },
      })

      const [macdData, signalData, histogramData] = calculateMACD(getClosePrices(data), 12, 26, 9)
      
      // MACD line
      const macdLine = macdChart.addSeries(LineSeries, {
        color: '#2196F3',
        lineWidth: 1,
      })
      macdLine.setData(macdData.map((v, i) => ({
        time: data[i].time as any,
        value: v ?? 0,
      })).filter((_, i) => macdData[i] !== null))

      // Signal line
      const signalLine = macdChart.addSeries(LineSeries, {
        color: '#FF9800',
        lineWidth: 1,
      })
      signalLine.setData(signalData.map((v, i) => ({
        time: data[i].time as any,
        value: v ?? 0,
      })).filter((_, i) => signalData[i] !== null))

      // Histogram
      const histogramSeries = macdChart.addSeries(HistogramSeries, {
        color: '#4CAF50',
      })
      histogramSeries.setData(histogramData.map((v, i) => ({
        time: data[i].time as any,
        value: v ?? 0,
        color: (v ?? 0) >= 0 ? chartColors.volumeUp : chartColors.volumeDown,
      })).filter((_, i) => histogramData[i] !== null))

      macdChart.timeScale().fitContent()
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
