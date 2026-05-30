'use client'

import type { UTCTimestamp } from 'lightweight-charts'

// Annotation types
export type AnnotationToolType = 'horizontal-line' | 'trend-line' | 'marker'

export interface HorizontalLineAnnotation {
  type: 'horizontal-line'
  id: string
  price: number
  color?: string
}

export interface TrendLineAnnotation {
  type: 'trend-line'
  id: string
  startTime: UTCTimestamp
  startPrice: number
  endTime: UTCTimestamp
  endPrice: number
  color?: string
}

export interface PriceMarkerAnnotation {
  type: 'marker'
  id: string
  time: UTCTimestamp
  price: number
  label?: string
  color?: string
}

export type Annotation =
  | HorizontalLineAnnotation
  | TrendLineAnnotation
  | PriceMarkerAnnotation

// Generate unique ID
export function generateAnnotationId(): string {
  return `ann_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
}

// localStorage helpers
const STORAGE_PREFIX = 'chart_annotations_'

export function getStorageKey(symbol: string): string {
  return `${STORAGE_PREFIX}${symbol}`
}

export function loadAnnotations(symbol: string): Annotation[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(getStorageKey(symbol))
    if (!raw) return []
    return JSON.parse(raw) as Annotation[]
  } catch {
    return []
  }
}

export function saveAnnotations(symbol: string, annotations: Annotation[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(getStorageKey(symbol), JSON.stringify(annotations))
  } catch {
    // Storage full or unavailable
  }
}

export function clearAnnotations(symbol: string): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(getStorageKey(symbol))
  } catch {
    // Ignore
  }
}

// Default colors for annotations
export const ANNOTATION_COLORS = {
  'horizontal-line': '#F59E0B',  // amber
  'trend-line': '#3B82F6',       // blue
  'marker': '#EF4444',           // red
}
