/**
 * Technical Indicator Calculations
 * Pure functions for calculating common technical indicators
 */

import type { Candle } from './types'
import type { Time } from 'lightweight-charts'

// ============================================================================
// Simple Moving Average (SMA)
// ============================================================================

export function calculateSMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      const slice = data.slice(i - period + 1, i + 1)
      const sum = slice.reduce((a, b) => a + b, 0)
      result.push(sum / period)
    }
  }
  return result
}

// ============================================================================
// Exponential Moving Average (EMA)
// ============================================================================

export function calculateEMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  const multiplier = 2 / (period + 1)

  // First EMA is SMA
  let ema: number | null = null
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else if (i === period - 1) {
      const slice = data.slice(0, period)
      ema = slice.reduce((a, b) => a + b, 0) / period
      result.push(ema)
    } else {
      ema = (data[i] - (ema ?? 0)) * multiplier + (ema ?? 0)
      result.push(ema)
    }
  }
  return result
}

// ============================================================================
// Relative Strength Index (RSI)
// ============================================================================

export function calculateRSI(data: number[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = []
  const gains: number[] = []
  const losses: number[] = []

  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      result.push(null)
      continue
    }

    const change = data[i] - data[i - 1]
    gains.push(change > 0 ? change : 0)
    losses.push(change < 0 ? Math.abs(change) : 0)

    if (i < period) {
      result.push(null)
    } else if (i === period) {
      const avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
      const avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
      result.push(100 - 100 / (1 + rs))
    } else {
      const avgGain =
        ((gains.slice(-period - 1, -1).reduce((a, b) => a + b, 0) / period) * (period - 1) +
          gains[gains.length - 1]) /
        period
      const avgLoss =
        ((losses.slice(-period - 1, -1).reduce((a, b) => a + b, 0) / period) * (period - 1) +
          losses[losses.length - 1]) /
        period
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
      result.push(100 - 100 / (1 + rs))
    }
  }
  return result
}

// ============================================================================
// MACD (Moving Average Convergence Divergence)
// ============================================================================

export interface MACDLine {
  time?: number
  macd: number | null
  signal: number | null
  histogram: number | null
}

export function calculateMACD(
  data: number[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): (number | null)[][] {
  const fastEMA = calculateEMA(data, fastPeriod)
  const slowEMA = calculateEMA(data, slowPeriod)

  // Calculate MACD line
  const macdLine: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (fastEMA[i] === null || slowEMA[i] === null) {
      macdLine.push(null)
    } else {
      macdLine.push((fastEMA[i] ?? 0) - (slowEMA[i] ?? 0))
    }
  }

  // Calculate Signal line (EMA of MACD)
  const validMACD = macdLine.filter((v): v is number => v !== null)
  const signalLine = calculateEMA(validMACD, signalPeriod)

  // Calculate Histogram
  const macdResult: (number | null)[] = []
  const signalResult: (number | null)[] = []
  const histogramResult: (number | null)[] = []
  let signalIdx = 0
  for (let i = 0; i < data.length; i++) {
    if (macdLine[i] === null) {
      macdResult.push(null)
      signalResult.push(null)
      histogramResult.push(null)
    } else {
      const signal = signalIdx < signalLine.length ? signalLine[signalIdx] : null
      const histogram = macdLine[i] !== null && signal !== null ? (macdLine[i] ?? 0) - signal : null
      macdResult.push(macdLine[i])
      signalResult.push(signal)
      histogramResult.push(histogram)
      signalIdx++
    }
  }
  return [macdResult, signalResult, histogramResult]
}

// ============================================================================
// Bollinger Bands
// ============================================================================

export interface BollingerBand {
  upper: number | null
  middle: number | null
  lower: number | null
}

export function calculateBollingerBands(
  data: number[],
  period: number = 20,
  stdDev: number = 2
): BollingerBand[] {
  const result: BollingerBand[] = []
  const sma = calculateSMA(data, period)

  for (let i = 0; i < data.length; i++) {
    if (sma[i] === null) {
      result.push({ upper: null, middle: null, lower: null })
    } else {
      const slice = data.slice(i - period + 1, i + 1)
      const mean = sma[i] ?? 0
      const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / period
      const std = Math.sqrt(variance)

      result.push({
        upper: mean + stdDev * std,
        middle: mean,
        lower: mean - stdDev * std,
      })
    }
  }
  return result
}

// ============================================================================
// ATR (Average True Range)
// ============================================================================

export function calculateATR(candles: Candle[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = []
  const trueRanges: number[] = []

  for (let i = 0; i < candles.length; i++) {
    if (i === 0) {
      trueRanges.push(candles[i].high - candles[i].low)
      result.push(null)
      continue
    }

    const tr = Math.max(
      candles[i].high - candles[i].low,
      Math.abs(candles[i].high - candles[i - 1].close),
      Math.abs(candles[i].low - candles[i - 1].close)
    )
    trueRanges.push(tr)

    if (i < period) {
      result.push(null)
    } else if (i === period) {
      const atr = trueRanges.slice(0, period).reduce((a, b) => a + b, 0) / period
      result.push(atr)
    } else {
      const prevATR = result[result.length - 1] ?? 0
      const atr = ((prevATR * (period - 1)) + tr) / period
      result.push(atr)
    }
  }
  return result
}

// ============================================================================
// Helper: Convert Candle data to close prices
// ============================================================================

export function getClosePrices(candles: Candle[]): number[] {
  return candles.map((c) => c.close)
}

// ============================================================================
// Helper: Format indicator data for lightweight-charts
// ============================================================================

export function formatIndicatorData(
  candles: Candle[],
  values: (number | null)[]
): { time: Time; value: number }[] {
  const result: { time: Time; value: number }[] = []
  for (let i = 0; i < candles.length; i++) {
    if (values[i] !== null) {
      result.push({ time: candles[i].time as Time, value: values[i] as number })
    }
  }
  return result
}
