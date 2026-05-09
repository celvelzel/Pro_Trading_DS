/**
 * Lobster Quant - TypeScript Type Definitions
 * Core types for the quantitative trading analysis platform.
 */

// ============================================================================
// Stock Data Types
// ============================================================================

export interface Candle {
  time: number      // Unix timestamp (seconds)
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface StockData {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume: number
  candles: Candle[]
}

// ============================================================================
// Technical Indicators
// ============================================================================

export interface MACDData {
  value: number
  signal: number
  histogram: number
}

export interface Indicators {
  rsi: number
  macd: MACDData
  ma20: number
  ma200: number
  atr: number
  atrPercent: number
}

// ============================================================================
// Trading Signals
// ============================================================================

export type SignalType = 'bullish' | 'bearish' | 'neutral'

export interface Signal {
  type: SignalType
  score: number        // 0-100
  probability: number  // 0-100
  reasons: string[]
}

// ============================================================================
// Options Analysis
// ============================================================================

export interface OptionsAnalysis {
  maxPain: number
  putCallRatio: number
  support: number[]
  resistance: number[]
}

// ============================================================================
// Risk Assessment
// ============================================================================

export type RiskStatus = 'on' | 'off'

export interface RiskAssessment {
  status: RiskStatus
  statusText: string
  reasons: string[]
  onPercent: number
  offPercent: number
}

// ============================================================================
// Scanner Types
// ============================================================================

export type Market = 'US' | 'HK' | 'A'

export interface ScanParams {
  market: Market
  minScore: number
}

export interface StockResult {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  score: number
  signalType: SignalType
  reasons: string[]
}

export interface ScanResponse {
  results: StockResult[]
  total: number
  market: Market
  minScore: number
}

// ============================================================================
// Backtest Types
// ============================================================================

export interface BacktestParams {
  symbol: string
  holdingDays: number
  minScore: number
  startDate?: string
  endDate?: string
}

export interface Trade {
  entryDate: string
  exitDate: string
  entryPrice: number
  exitPrice: number
  returnPercent: number
  holdingDays: number
}

export interface EquityPoint {
  date: string
  value: number
}

export interface BacktestResult {
  totalTrades: number
  winRate: number
  totalReturn: number
  maxDrawdown: number
  sharpeRatio: number
  trades: Trade[]
  equityCurve: EquityPoint[]
}

// ============================================================================
// Settings Types
// ============================================================================

export interface MarketSettings {
  enableUS: boolean
  enableHK: boolean
  enableA: boolean
}

export interface DataSettings {
  dataYears: number
  cacheTTL: number
}

export interface ScoringWeights {
  trend: number
  momentum: number
  volume: number
  pattern: number
}

export interface AppSettings {
  markets: MarketSettings
  data: DataSettings
  scoring: ScoringWeights
  theme: 'light' | 'dark'
}

// ============================================================================
// UI Types
// ============================================================================

export type Timeframe = '1D' | '1W' | '1M' | '3M' | '1Y'

export interface ChartConfig {
  timeframe: Timeframe
  showVolume: boolean
  showRSI: boolean
  showMACD: boolean
  showMA20: boolean
  showMA200: boolean
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}

export interface ApiError {
  detail: string
  status: number
}
