'use client'

import { useState, useCallback, useEffect, memo } from 'react'
import { CandlestickChart } from './CandlestickChart'
import { AnnotationToolbar } from './AnnotationToolbar'
import type { Annotation, AnnotationToolType } from './annotations'
import { loadAnnotations, saveAnnotations, clearAnnotations } from './annotations'
import type { Candle } from '@/lib/types'
import type { IndicatorType } from './IndicatorToggle'

interface AnnotatedCandlestickChartProps {
  data: Candle[]
  symbol: string
  height?: number
  showVolume?: boolean
  activeIndicators?: IndicatorType[]
  className?: string
}

/**
 * AnnotatedCandlestickChart - Wraps CandlestickChart with annotation tools,
 * toolbar, and localStorage persistence.
 */
export const AnnotatedCandlestickChart = memo(function AnnotatedCandlestickChart({
  data,
  symbol,
  height = 400,
  showVolume = true,
  activeIndicators = [],
  className,
}: AnnotatedCandlestickChartProps) {
  const [annotations, setAnnotations] = useState<Annotation[]>([])
  const [activeTool, setActiveTool] = useState<AnnotationToolType | null>(null)

  // Load annotations from localStorage on mount / symbol change
  useEffect(() => {
    const saved = loadAnnotations(symbol)
    setAnnotations(saved)
  }, [symbol])

  // Save annotations to localStorage whenever they change
  useEffect(() => {
    saveAnnotations(symbol, annotations)
  }, [symbol, annotations])

  const handleAnnotationAdd = useCallback((annotation: Annotation) => {
    setAnnotations((prev) => [...prev, annotation])
  }, [])

  const handleClearAll = useCallback(() => {
    setAnnotations([])
    clearAnnotations(symbol)
  }, [symbol])

  return (
    <div className={className}>
      <AnnotationToolbar
        activeTool={activeTool}
        onSelectTool={setActiveTool}
        onClearAll={handleClearAll}
        annotationCount={annotations.length}
        className="mb-2"
      />
      <CandlestickChart
        data={data}
        symbol={symbol}
        height={height}
        showVolume={showVolume}
        activeIndicators={activeIndicators}
        annotations={annotations}
        activeAnnotationTool={activeTool}
        onAnnotationAdd={handleAnnotationAdd}
      />
    </div>
  )
})
