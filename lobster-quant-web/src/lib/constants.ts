/**
 * Lobster Quant - Constants
 * Application-wide constants and configuration.
 */

// ============================================================================
// API Configuration
// ============================================================================

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

// ============================================================================
// Stock Lists
// ============================================================================

export const STOCK_LISTS: Record<string, string[]> = {
  US: [
    'AIPO', 'AMZN', 'COHR', 'GLW', 'GOOG', 'ICLN', 'LITE', 'MU',
    'QQQ', 'SPY', 'TSLA', 'URA', 'VTI', 'XLE', 'XLU'
  ],
  HK: [
    '0005.HK', '0700.HK', '1299.HK', '2318.HK', '3690.HK',
    '9988.HK', '1810.HK', '2269.HK', '2020.HK', '9618.HK'
  ],
  A: [
    '600519', '000001', '300308', '002594', '600036',
    '000333', '300750', '601318', '600276', '002415'
  ],
}

// ============================================================================
// Chart Configuration
// ============================================================================

export const TIMEFRAMES = ['1D', '1W', '1M', '3M', '1Y'] as const

export const CHART_COLORS = {
  light: {
    up: '#34A853',
    down: '#EA4335',
    neutral: '#9AA0A6',
    grid: '#F0F0F0',
    background: '#FFFFFF',
    text: '#202124',
  },
  dark: {
    up: '#81C995',
    down: '#F28B82',
    neutral: '#9AA0A6',
    grid: '#3C4043',
    background: '#202124',
    text: '#E8EAED',
  },
} as const

// ============================================================================
// Scoring Configuration
// ============================================================================

export const DEFAULT_SCORING_WEIGHTS = {
  trend: 0.3,
  momentum: 0.3,
  volume: 0.2,
  pattern: 0.2,
} as const

export const SCORE_THRESHOLDS = {
  bullish: 70,
  neutral: 40,
  bearish: 0,
} as const

// ============================================================================
// Backtest Configuration
// ============================================================================

export const DEFAULT_BACKTEST_PARAMS = {
  holdingDays: 10,
  minScore: 60,
} as const

// ============================================================================
// UI Configuration
// ============================================================================

export const SIDEBAR_WIDTH = 256  // 64 * 4 (w-64 in Tailwind)
export const HEADER_HEIGHT = 56   // 14 * 4 (h-14 in Tailwind)
export const MOBILE_NAV_HEIGHT = 64  // 16 * 4 (h-16 in Tailwind)

// ============================================================================
// Query Configuration (React Query)
// ============================================================================

export const QUERY_CONFIG = {
  staleTime: 5 * 60 * 1000,      // 5 minutes
  gcTime: 10 * 60 * 1000,        // 10 minutes (formerly cacheTime)
  retryCount: 3,
  refetchInterval: false,         // No auto-refetch by default
} as const

// ============================================================================
// Theme Configuration
// ============================================================================

export const THEMES = {
  light: 'light',
  dark: 'dark',
} as const

export type Theme = keyof typeof THEMES
