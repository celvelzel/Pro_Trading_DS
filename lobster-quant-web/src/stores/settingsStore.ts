import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { DEFAULT_SCORING_WEIGHTS } from '@/lib/constants'
import type {
  MarketSettings,
  DataSettings,
  ScoringWeights,
  BacktestSettings,
  OFFFilterSettings,
  IndicatorSettings,
  AppSettings,
} from '@/lib/types'

// ============================================================================
// Default Values (aligned with backend lobster_quant/src/config/settings.py)
// ============================================================================

const DEFAULT_MARKET_SETTINGS: MarketSettings = {
  enableUS: true,
  enableHK: true,
  enableA: false,
}

const DEFAULT_DATA_SETTINGS: DataSettings = {
  dataYears: 3,
  cacheTTL: 3600,
}

const DEFAULT_SCORING: ScoringWeights = {
  trend: DEFAULT_SCORING_WEIGHTS.trend,
  momentum: DEFAULT_SCORING_WEIGHTS.momentum,
  volume: DEFAULT_SCORING_WEIGHTS.volume,
  pattern: DEFAULT_SCORING_WEIGHTS.pattern,
}

const DEFAULT_BACKTEST_SETTINGS: BacktestSettings = {
  holdingDays: 20,
  minScore: 20,
  lookbackDays: 500,
  slippagePct: 0.001,
  commissionPct: 0.001,
}

const DEFAULT_OFF_FILTER: OFFFilterSettings = {
  vixThreshold: 35.0,
  atrPctThreshold: 0.05,
  gapThreshold: 0.08,
  minVolumeRatio: 0.05,
  ma200RecoveryDays: 60,
}

const DEFAULT_INDICATORS: IndicatorSettings = {
  maShortPeriod: 20,
  maLongPeriod: 200,
  rsiPeriod: 14,
  atrPeriod: 14,
  macdFast: 12,
  macdSlow: 26,
  macdSignal: 9,
  bbPeriod: 20,
  bbStd: 2.0,
}

// ============================================================================
// Store Interface
// ============================================================================

interface SettingsState {
  // Market settings
  enableUS: boolean
  enableHK: boolean
  enableA: boolean

  // Data settings
  dataYears: number
  cacheTTL: number

  // Scoring weights
  trendWeight: number
  momentumWeight: number
  volumeWeight: number
  patternWeight: number

  // Backtest settings
  holdingDays: number
  minScore: number
  lookbackDays: number
  slippagePct: number
  commissionPct: number

  // OFF filter settings
  vixThreshold: number
  atrPctThreshold: number
  gapThreshold: number
  minVolumeRatio: number
  ma200RecoveryDays: number

  // Indicator settings
  maShortPeriod: number
  maLongPeriod: number
  rsiPeriod: number
  atrPeriod: number
  macdFast: number
  macdSlow: number
  macdSignal: number
  bbPeriod: number
  bbStd: number

  // Benchmark
  benchmarkSymbol: string

  // Actions
  setMarkets: (markets: Partial<MarketSettings>) => void
  setDataSettings: (settings: Partial<DataSettings>) => void
  setScoringWeights: (weights: Partial<ScoringWeights>) => void
  setBacktestSettings: (settings: Partial<BacktestSettings>) => void
  setOFFFilter: (settings: Partial<OFFFilterSettings>) => void
  setIndicators: (settings: Partial<IndicatorSettings>) => void
  setBenchmark: (symbol: string) => void
  resetToDefaults: () => void

  /** Export current state as AppSettings for API sync. */
  toAppSettings: () => AppSettings

  /** Import AppSettings from API response. */
  fromAppSettings: (settings: AppSettings) => void
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      // Market settings
      enableUS: DEFAULT_MARKET_SETTINGS.enableUS,
      enableHK: DEFAULT_MARKET_SETTINGS.enableHK,
      enableA: DEFAULT_MARKET_SETTINGS.enableA,

      // Data settings
      dataYears: DEFAULT_DATA_SETTINGS.dataYears,
      cacheTTL: DEFAULT_DATA_SETTINGS.cacheTTL,

      // Scoring weights
      trendWeight: DEFAULT_SCORING.trend,
      momentumWeight: DEFAULT_SCORING.momentum,
      volumeWeight: DEFAULT_SCORING.volume,
      patternWeight: DEFAULT_SCORING.pattern,

      // Backtest settings
      holdingDays: DEFAULT_BACKTEST_SETTINGS.holdingDays,
      minScore: DEFAULT_BACKTEST_SETTINGS.minScore,
      lookbackDays: DEFAULT_BACKTEST_SETTINGS.lookbackDays,
      slippagePct: DEFAULT_BACKTEST_SETTINGS.slippagePct,
      commissionPct: DEFAULT_BACKTEST_SETTINGS.commissionPct,

      // OFF filter settings
      vixThreshold: DEFAULT_OFF_FILTER.vixThreshold,
      atrPctThreshold: DEFAULT_OFF_FILTER.atrPctThreshold,
      gapThreshold: DEFAULT_OFF_FILTER.gapThreshold,
      minVolumeRatio: DEFAULT_OFF_FILTER.minVolumeRatio,
      ma200RecoveryDays: DEFAULT_OFF_FILTER.ma200RecoveryDays,

      // Indicator settings
      maShortPeriod: DEFAULT_INDICATORS.maShortPeriod,
      maLongPeriod: DEFAULT_INDICATORS.maLongPeriod,
      rsiPeriod: DEFAULT_INDICATORS.rsiPeriod,
      atrPeriod: DEFAULT_INDICATORS.atrPeriod,
      macdFast: DEFAULT_INDICATORS.macdFast,
      macdSlow: DEFAULT_INDICATORS.macdSlow,
      macdSignal: DEFAULT_INDICATORS.macdSignal,
      bbPeriod: DEFAULT_INDICATORS.bbPeriod,
      bbStd: DEFAULT_INDICATORS.bbStd,

      // Benchmark
      benchmarkSymbol: 'SPY',

      // Actions
      setMarkets: (markets) => set((state) => ({ ...state, ...markets })),

      setDataSettings: (settings) => set((state) => ({ ...state, ...settings })),

      setScoringWeights: (weights) => set((state) => ({ ...state, ...weights })),

      setBacktestSettings: (settings) => set((state) => ({ ...state, ...settings })),

      setOFFFilter: (settings) => set((state) => ({ ...state, ...settings })),

      setIndicators: (settings) => set((state) => ({ ...state, ...settings })),

      setBenchmark: (symbol) => set({ benchmarkSymbol: symbol }),

      resetToDefaults: () => set({
        ...DEFAULT_MARKET_SETTINGS,
        dataYears: DEFAULT_DATA_SETTINGS.dataYears,
        cacheTTL: DEFAULT_DATA_SETTINGS.cacheTTL,
        trendWeight: DEFAULT_SCORING.trend,
        momentumWeight: DEFAULT_SCORING.momentum,
        volumeWeight: DEFAULT_SCORING.volume,
        patternWeight: DEFAULT_SCORING.pattern,
        ...DEFAULT_BACKTEST_SETTINGS,
        ...DEFAULT_OFF_FILTER,
        ...DEFAULT_INDICATORS,
        benchmarkSymbol: 'SPY',
      }),

      toAppSettings: (): AppSettings => {
        const s = get()
        return {
          markets: { enableUS: s.enableUS, enableHK: s.enableHK, enableA: s.enableA },
          data: { dataYears: s.dataYears, cacheTTL: s.cacheTTL },
          scoring: { trend: s.trendWeight, momentum: s.momentumWeight, volume: s.volumeWeight, pattern: s.patternWeight },
          backtest: { holdingDays: s.holdingDays, minScore: s.minScore, lookbackDays: s.lookbackDays, slippagePct: s.slippagePct, commissionPct: s.commissionPct },
          offFilter: { vixThreshold: s.vixThreshold, atrPctThreshold: s.atrPctThreshold, gapThreshold: s.gapThreshold, minVolumeRatio: s.minVolumeRatio, ma200RecoveryDays: s.ma200RecoveryDays },
          indicators: { maShortPeriod: s.maShortPeriod, maLongPeriod: s.maLongPeriod, rsiPeriod: s.rsiPeriod, atrPeriod: s.atrPeriod, macdFast: s.macdFast, macdSlow: s.macdSlow, macdSignal: s.macdSignal, bbPeriod: s.bbPeriod, bbStd: s.bbStd },
          benchmarkSymbol: s.benchmarkSymbol,
        }
      },

      fromAppSettings: (settings: AppSettings) => set({
        enableUS: settings.markets.enableUS,
        enableHK: settings.markets.enableHK,
        enableA: settings.markets.enableA,
        dataYears: settings.data.dataYears,
        cacheTTL: settings.data.cacheTTL,
        trendWeight: settings.scoring.trend,
        momentumWeight: settings.scoring.momentum,
        volumeWeight: settings.scoring.volume,
        patternWeight: settings.scoring.pattern,
        holdingDays: settings.backtest.holdingDays,
        minScore: settings.backtest.minScore,
        lookbackDays: settings.backtest.lookbackDays,
        slippagePct: settings.backtest.slippagePct,
        commissionPct: settings.backtest.commissionPct,
        vixThreshold: settings.offFilter.vixThreshold,
        atrPctThreshold: settings.offFilter.atrPctThreshold,
        gapThreshold: settings.offFilter.gapThreshold,
        minVolumeRatio: settings.offFilter.minVolumeRatio,
        ma200RecoveryDays: settings.offFilter.ma200RecoveryDays,
        maShortPeriod: settings.indicators.maShortPeriod,
        maLongPeriod: settings.indicators.maLongPeriod,
        rsiPeriod: settings.indicators.rsiPeriod,
        atrPeriod: settings.indicators.atrPeriod,
        macdFast: settings.indicators.macdFast,
        macdSlow: settings.indicators.macdSlow,
        macdSignal: settings.indicators.macdSignal,
        bbPeriod: settings.indicators.bbPeriod,
        bbStd: settings.indicators.bbStd,
        benchmarkSymbol: settings.benchmarkSymbol,
      }),
    }),
    {
      name: 'settings-storage',
    }
  )
)
