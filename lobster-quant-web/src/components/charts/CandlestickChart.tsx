'use client'

import { useEffect, useRef, memo } from 'react'
import { useTheme } from 'next-themes'
import { createChart, IChartApi, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers, type UTCTimestamp, type MouseEventParams } from 'lightweight-charts'
import type { Candle } from '@/lib/types'
import type { IndicatorType } from './IndicatorToggle'
import { calculateSMA, calculateEMA, calculateBollingerBands, getClosePrices, formatIndicatorData } from '@/lib/indicators'
import type { Annotation, AnnotationToolType, HorizontalLineAnnotation, TrendLineAnnotation, PriceMarkerAnnotation } from './annotations'
import { ANNOTATION_COLORS } from './annotations'

/** Read a design-system CSS custom property from the document root. */
function cssVar(name: string): string {
  if (typeof window === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/** Append an alpha channel to a #rrggbb color; other formats pass through. */
function withAlpha(color: string, alpha: string): string {
  return /^#[0-9a-fA-F]{6}$/.test(color) ? `${color}${alpha}` : color
}

interface CandlestickChartProps {
  data: Candle[]
  symbol: string
  height?: number
  showVolume?: boolean
  activeIndicators?: IndicatorType[]
  className?: string
  /** Current annotations to render */
  annotations?: Annotation[]
  /** Active annotation tool (null = no tool selected) */
  activeAnnotationTool?: AnnotationToolType | null
  /** Called when user clicks chart with an annotation tool active */
  onAnnotationAdd?: (annotation: Annotation) => void
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
  annotations = [],
  activeAnnotationTool = null,
  onAnnotationAdd,
}: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null)
  const pendingTrendStartRef = useRef<{ time: UTCTimestamp; price: number } | null>(null)
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

  // Reset pending trend start when tool changes
  useEffect(() => {
    if (activeAnnotationTool !== 'trend-line') {
      pendingTrendStartRef.current = null
    }
  }, [activeAnnotationTool])

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return

    // Theme-aware colors resolved from design-system CSS variables so the
    // chart always matches the active light/dark theme. The effect re-runs
    // when the resolved theme changes, re-applying these options.
    const chartColors = {
      background: cssVar('--card'),
      text: cssVar('--muted-foreground'),
      grid: cssVar('--border'),
      border: cssVar('--border'),
      crosshair: cssVar('--color-text-tertiary'),
      upColor: cssVar('--color-success'),
      downColor: cssVar('--color-error'),
      volumeUp: withAlpha(cssVar('--color-success'), isDark ? '4D' : '80'),
      volumeDown: withAlpha(cssVar('--color-error'), isDark ? '4D' : '80'),
      sma20: cssVar('--chart-1'),
      sma50: cssVar('--chart-3'),
      sma200: cssVar('--chart-4'),
      ema12: cssVar('--chart-2'),
      ema26: cssVar('--chart-5'),
      bands: cssVar('--muted-foreground'),
    }

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
        vertLine: { color: chartColors.crosshair },
        horzLine: { color: chartColors.crosshair },
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

    // Store series reference for annotations
    candlestickSeriesRef.current = candlestickSeries

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

        chart.addSeries(LineSeries, { color: chartColors.sma20, lineWidth: 1 })
          .setData(formatIndicatorData(data, sma20))
        chart.addSeries(LineSeries, { color: chartColors.sma50, lineWidth: 1 })
          .setData(formatIndicatorData(data, sma50))
        chart.addSeries(LineSeries, { color: chartColors.sma200, lineWidth: 1 })
          .setData(formatIndicatorData(data, sma200))
      }

      // EMA overlays
      if (activeIndicators.includes('ema')) {
        const ema12 = calculateEMA(closePrices, 12)
        const ema26 = calculateEMA(closePrices, 26)

        chart.addSeries(LineSeries, { color: chartColors.ema12, lineWidth: 1 })
          .setData(formatIndicatorData(data, ema12))
        chart.addSeries(LineSeries, { color: chartColors.ema26, lineWidth: 1 })
          .setData(formatIndicatorData(data, ema26))
      }

      // Bollinger Bands overlays
      if (activeIndicators.includes('bb')) {
        const bbData = calculateBollingerBands(closePrices, 20, 2)
        const upper = bbData.map(d => d.upper)
        const middle = bbData.map(d => d.middle)
        const lower = bbData.map(d => d.lower)

        chart.addSeries(LineSeries, { color: chartColors.bands, lineWidth: 1 })
          .setData(formatIndicatorData(data, upper))
        chart.addSeries(LineSeries, { color: withAlpha(chartColors.bands, '80'), lineWidth: 1 })
          .setData(formatIndicatorData(data, lower))
        chart.addSeries(LineSeries, { color: withAlpha(chartColors.bands, '40'), lineWidth: 1 })
          .setData(formatIndicatorData(data, middle))
      }
    }

    // --- Render annotations ---
    // Horizontal lines
    const horizontalAnnotations = annotations.filter(
      (a): a is HorizontalLineAnnotation => a.type === 'horizontal-line'
    )
    for (const ann of horizontalAnnotations) {
      candlestickSeries.createPriceLine({
        price: ann.price,
        color: ann.color ?? ANNOTATION_COLORS['horizontal-line'],
        lineWidth: 1,
        lineStyle: 0,
        axisLabelVisible: true,
        title: '',
      })
    }

    // Trend lines
    const trendAnnotations = annotations.filter(
      (a): a is TrendLineAnnotation => a.type === 'trend-line'
    )
    for (const ann of trendAnnotations) {
      chart.addSeries(LineSeries, {
        color: ann.color ?? ANNOTATION_COLORS['trend-line'],
        lineWidth: 2,
        lineStyle: 0,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      }).setData([
        { time: ann.startTime, value: ann.startPrice },
        { time: ann.endTime, value: ann.endPrice },
      ])
    }

    // Price markers
    const markerAnnotations = annotations.filter(
      (a): a is PriceMarkerAnnotation => a.type === 'marker'
    )
    if (markerAnnotations.length > 0) {
      const markers = markerAnnotations.map((ann) => ({
        time: ann.time,
        position: 'belowBar' as const,
        color: ann.color ?? ANNOTATION_COLORS['marker'],
        shape: 'arrowUp' as const,
        text: ann.label ?? '',
        id: ann.id,
      }))
      createSeriesMarkers(candlestickSeries, markers)
    }

    // --- Click handler for annotations ---
    const clickHandler = (param: MouseEventParams) => {
      if (!activeAnnotationTool || !param.time || !param.point || !onAnnotationAdd) return

      const price = candlestickSeries.coordinateToPrice(param.point.y)
      if (price === null || price === undefined) return

      const time = param.time as UTCTimestamp

      if (activeAnnotationTool === 'horizontal-line') {
        onAnnotationAdd({
          type: 'horizontal-line',
          id: `ann_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
          price,
        })
      } else if (activeAnnotationTool === 'trend-line') {
        if (!pendingTrendStartRef.current) {
          pendingTrendStartRef.current = { time, price }
        } else {
          const start = pendingTrendStartRef.current
          pendingTrendStartRef.current = null
          onAnnotationAdd({
            type: 'trend-line',
            id: `ann_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
            startTime: start.time,
            startPrice: start.price,
            endTime: time,
            endPrice: price,
          })
        }
      } else if (activeAnnotationTool === 'marker') {
        onAnnotationAdd({
          type: 'marker',
          id: `ann_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
          time,
          price,
        })
      }
    }

    chart.subscribeClick(clickHandler)

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
      chart.unsubscribeClick(clickHandler)
      chart.remove()
      chartRef.current = null
      candlestickSeriesRef.current = null
    }
  }, [data, height, showVolume, activeIndicators, isDark, annotations, activeAnnotationTool, onAnnotationAdd])

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
