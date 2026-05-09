import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { DEFAULT_SCORING_WEIGHTS } from '@/lib/constants'

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
  
  // Actions
  setMarkets: (markets: { enableUS?: boolean; enableHK?: boolean; enableA?: boolean }) => void
  setDataSettings: (settings: { dataYears?: number; cacheTTL?: number }) => void
  setScoringWeights: (weights: { trend?: number; momentum?: number; volume?: number; pattern?: number }) => void
  resetToDefaults: () => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      // Market settings defaults
      enableUS: true,
      enableHK: true,
      enableA: false,
      
      // Data settings defaults
      dataYears: 5,
      cacheTTL: 300,
      
      // Scoring weights defaults
      trendWeight: DEFAULT_SCORING_WEIGHTS.trend,
      momentumWeight: DEFAULT_SCORING_WEIGHTS.momentum,
      volumeWeight: DEFAULT_SCORING_WEIGHTS.volume,
      patternWeight: DEFAULT_SCORING_WEIGHTS.pattern,
      
      // Actions
      setMarkets: (markets) => set((state) => ({
        ...state,
        ...markets,
      })),
      
      setDataSettings: (settings) => set((state) => ({
        ...state,
        ...settings,
      })),
      
      setScoringWeights: (weights) => set((state) => ({
        ...state,
        ...weights,
      })),
      
      resetToDefaults: () => set({
        enableUS: true,
        enableHK: true,
        enableA: false,
        dataYears: 5,
        cacheTTL: 300,
        trendWeight: DEFAULT_SCORING_WEIGHTS.trend,
        momentumWeight: DEFAULT_SCORING_WEIGHTS.momentum,
        volumeWeight: DEFAULT_SCORING_WEIGHTS.volume,
        patternWeight: DEFAULT_SCORING_WEIGHTS.pattern,
      }),
    }),
    {
      name: 'settings-storage',
    }
  )
)
