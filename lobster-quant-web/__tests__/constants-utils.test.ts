/**
 * Unit tests for constants.ts and utils.ts
 * Tests application constants and utility functions.
 */
import { describe, it, expect } from 'vitest'
import { cn } from '@/lib/utils'
import {
  STOCK_LISTS,
  TIMEFRAMES,
  CHART_COLORS,
  DEFAULT_SCORING_WEIGHTS,
  SCORE_THRESHOLDS,
  DEFAULT_BACKTEST_PARAMS,
} from '@/lib/constants'

// ─── cn utility ─────────────────────────────────────────────────

describe('cn (className utility)', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
  })

  it('handles undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar')
  })

  it('merges tailwind classes correctly', () => {
    // twMerge should handle conflicting classes
    const result = cn('p-4', 'p-8')
    expect(result).toBe('p-8')
  })

  it('handles arrays', () => {
    expect(cn(['foo', 'bar'])).toBe('foo bar')
  })

  it('handles objects', () => {
    expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz')
  })
})

// ─── STOCK_LISTS ────────────────────────────────────────────────

describe('STOCK_LISTS', () => {
  it('has US stocks', () => {
    expect(STOCK_LISTS.US).toBeDefined()
    expect(STOCK_LISTS.US.length).toBeGreaterThan(0)
    expect(STOCK_LISTS.US).toContain('SPY')
    expect(STOCK_LISTS.US).toContain('TSLA')
  })

  it('has HK stocks', () => {
    expect(STOCK_LISTS.HK).toBeDefined()
    expect(STOCK_LISTS.HK.length).toBeGreaterThan(0)
    expect(STOCK_LISTS.HK).toContain('0700.HK')
  })

  it('has A-shares', () => {
    expect(STOCK_LISTS.A).toBeDefined()
    expect(STOCK_LISTS.A.length).toBeGreaterThan(0)
    expect(STOCK_LISTS.A).toContain('600519')
  })
})

// ─── TIMEFRAMES ─────────────────────────────────────────────────

describe('TIMEFRAMES', () => {
  it('has correct timeframes', () => {
    expect(TIMEFRAMES).toEqual(['1D', '1W', '1M', '3M', '1Y'])
  })

  it('is a readonly tuple', () => {
    // TIMEFRAMES is `as const`, so it should be readonly
    expect(TIMEFRAMES.length).toBe(5)
  })
})

// ─── CHART_COLORS ───────────────────────────────────────────────

describe('CHART_COLORS', () => {
  it('has light theme colors', () => {
    expect(CHART_COLORS.light.up).toBeTruthy()
    expect(CHART_COLORS.light.down).toBeTruthy()
    expect(CHART_COLORS.light.background).toBeTruthy()
  })

  it('has dark theme colors', () => {
    expect(CHART_COLORS.dark.up).toBeTruthy()
    expect(CHART_COLORS.dark.down).toBeTruthy()
    expect(CHART_COLORS.dark.background).toBeTruthy()
  })

  it('light and dark have different backgrounds', () => {
    expect(CHART_COLORS.light.background).not.toBe(CHART_COLORS.dark.background)
  })
})

// ─── DEFAULT_SCORING_WEIGHTS ────────────────────────────────────

describe('DEFAULT_SCORING_WEIGHTS', () => {
  it('has all weight categories', () => {
    expect(DEFAULT_SCORING_WEIGHTS.trend).toBeDefined()
    expect(DEFAULT_SCORING_WEIGHTS.momentum).toBeDefined()
    expect(DEFAULT_SCORING_WEIGHTS.volume).toBeDefined()
    expect(DEFAULT_SCORING_WEIGHTS.pattern).toBeDefined()
  })

  it('weights sum to 1.0', () => {
    const sum =
      DEFAULT_SCORING_WEIGHTS.trend +
      DEFAULT_SCORING_WEIGHTS.momentum +
      DEFAULT_SCORING_WEIGHTS.volume +
      DEFAULT_SCORING_WEIGHTS.pattern
    expect(sum).toBeCloseTo(1.0)
  })
})

// ─── SCORE_THRESHOLDS ───────────────────────────────────────────

describe('SCORE_THRESHOLDS', () => {
  it('has correct threshold values', () => {
    expect(SCORE_THRESHOLDS.bullish).toBe(70)
    expect(SCORE_THRESHOLDS.neutral).toBe(40)
    expect(SCORE_THRESHOLDS.bearish).toBe(0)
  })

  it('thresholds are in descending order', () => {
    expect(SCORE_THRESHOLDS.bullish).toBeGreaterThan(SCORE_THRESHOLDS.neutral)
    expect(SCORE_THRESHOLDS.neutral).toBeGreaterThan(SCORE_THRESHOLDS.bearish)
  })
})

// ─── DEFAULT_BACKTEST_PARAMS ────────────────────────────────────

describe('DEFAULT_BACKTEST_PARAMS', () => {
  it('has holding days', () => {
    expect(DEFAULT_BACKTEST_PARAMS.holdingDays).toBe(10)
  })

  it('has minimum score', () => {
    expect(DEFAULT_BACKTEST_PARAMS.minScore).toBe(60)
  })
})
