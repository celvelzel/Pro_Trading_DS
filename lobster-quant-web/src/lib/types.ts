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

export interface SignalHistoryEntry {
  date: string
  score: number
  signalType: SignalType
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
  probability: number
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
  slippagePct?: number
  commissionPct?: number
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

export interface BacktestSettings {
  holdingDays: number
  minScore: number
  lookbackDays: number
  slippagePct: number
  commissionPct: number
}

export interface OFFFilterSettings {
  vixThreshold: number
  atrPctThreshold: number
  gapThreshold: number
  minVolumeRatio: number
  ma200RecoveryDays: number
}

export interface IndicatorSettings {
  maShortPeriod: number
  maLongPeriod: number
  rsiPeriod: number
  atrPeriod: number
  macdFast: number
  macdSlow: number
  macdSignal: number
  bbPeriod: number
  bbStd: number
}

export interface AppSettings {
  markets: MarketSettings
  data: DataSettings
  scoring: ScoringWeights
  backtest: BacktestSettings
  offFilter: OFFFilterSettings
  indicators: IndicatorSettings
  benchmarkSymbol: string
}

/** Partial settings update — only provided fields are applied. */
export type SettingsUpdateRequest = {
  [K in keyof AppSettings]?: AppSettings[K]
}

export interface SettingsResponse {
  settings: AppSettings
  success: boolean
  message?: string
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
// Alert Types
// ============================================================================

export type AlertCondition = 'score_above' | 'score_below' | 'price_above' | 'price_below' | 'signal_change'

export interface AlertRule {
  id: string
  symbol: string
  condition: AlertCondition
  threshold: number
  enabled: boolean
  createdAt: string
  triggeredAt: string | null
}

export interface TriggeredAlert {
  id: string
  ruleId: string
  symbol: string
  condition: AlertCondition
  threshold: number
  currentValue: number
  message: string
  triggeredAt: string
  read: boolean
}

export interface AlertRulesResponse {
  rules: AlertRule[]
}

export interface TriggeredAlertsResponse {
  alerts: TriggeredAlert[]
  unreadCount: number
}

export interface CreateAlertRuleRequest {
  symbol: string
  condition: AlertCondition
  threshold: number
  enabled?: boolean
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
