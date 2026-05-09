'use client'

import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts'
import type { Candle } from '@/lib/types'

interface CandlestickChartProps {
  data: Candle[]
  symbol: string
  height?: number
  showVolume?: boolean
  className?: string
}

export function CandlestickChart({
  data,
  symbol,
  height = 400,
  showVolume = true,
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

    // Fit content
    chart.timeScale().fitContent()

    // Store chart reference
    chartRef.current = chart

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
    }
  }, [data, height, showVolume])

  return (
    <div
      ref={chartContainerRef}
      className={className}
      style={{ width: '100%', height: `${height}px` }}
    />
  )
}
