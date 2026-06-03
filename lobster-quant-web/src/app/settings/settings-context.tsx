'use client'

import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { useSettings, useUpdateSettings, useResetSettings } from '@/hooks/useSettings'
import type { AppSettings } from '@/lib/types'

// ============================================================================
// Validation Helpers
// ============================================================================

export interface ValidationErrors {
  [key: string]: string
}

export function validateScoringWeights(
  trend: number,
  momentum: number,
  volume: number,
  pattern: number
): ValidationErrors {
  const errors: ValidationErrors = {}
  const total = trend + momentum + volume + pattern
  if (Math.abs(total - 1) > 0.05) {
    errors.scoringTotal = `Weights sum to ${total.toFixed(2)}, should be ~1.00`
  }
  return errors
}

export function validateBacktest(
  holdingDays: number,
  minScore: number,
  lookbackDays: number,
  slippagePct: number,
  commissionPct: number
): ValidationErrors {
  const errors: ValidationErrors = {}
  if (holdingDays < 5 || holdingDays > 100) errors.holdingDays = 'Must be 5-100'
  if (minScore < 0 || minScore > 100) errors.minScore = 'Must be 0-100'
  if (lookbackDays < 100 || lookbackDays > 2000) errors.lookbackDays = 'Must be 100-2000'
  if (slippagePct < 0 || slippagePct > 0.01) errors.slippagePct = 'Must be 0-1%'
  if (commissionPct < 0 || commissionPct > 0.01) errors.commissionPct = 'Must be 0-1%'
  return errors
}

export function validateOFFFilter(
  vixThreshold: number,
  atrPctThreshold: number,
  gapThreshold: number,
  minVolumeRatio: number,
  ma200RecoveryDays: number
): ValidationErrors {
  const errors: ValidationErrors = {}
  if (vixThreshold < 10 || vixThreshold > 100) errors.vixThreshold = 'Must be 10-100'
  if (atrPctThreshold < 0.01 || atrPctThreshold > 0.2) errors.atrPctThreshold = 'Must be 1-20%'
  if (gapThreshold < 0.01 || gapThreshold > 0.3) errors.gapThreshold = 'Must be 1-30%'
  if (minVolumeRatio < 0 || minVolumeRatio > 1) errors.minVolumeRatio = 'Must be 0-1'
  if (ma200RecoveryDays < 10 || ma200RecoveryDays > 200) errors.ma200RecoveryDays = 'Must be 10-200'
  return errors
}

export function validateIndicators(
  maShortPeriod: number,
  maLongPeriod: number,
  rsiPeriod: number,
  atrPeriod: number,
  macdFast: number,
  macdSlow: number,
  macdSignal: number,
  bbPeriod: number,
  bbStd: number
): ValidationErrors {
  const errors: ValidationErrors = {}
  if (maShortPeriod < 5 || maShortPeriod > 100) errors.maShortPeriod = 'Must be 5-100'
  if (maLongPeriod < 50 || maLongPeriod > 500) errors.maLongPeriod = 'Must be 50-500'
  if (maShortPeriod >= maLongPeriod) errors.maLongPeriod = 'Long period must exceed short'
  if (rsiPeriod < 5 || rsiPeriod > 50) errors.rsiPeriod = 'Must be 5-50'
  if (atrPeriod < 5 || atrPeriod > 50) errors.atrPeriod = 'Must be 5-50'
  if (macdFast < 5 || macdFast > 50) errors.macdFast = 'Must be 5-50'
  if (macdSlow < 10 || macdSlow > 100) errors.macdSlow = 'Must be 10-100'
  if (macdFast >= macdSlow) errors.macdSlow = 'Slow must exceed fast'
  if (macdSignal < 5 || macdSignal > 50) errors.macdSignal = 'Must be 5-50'
  if (bbPeriod < 5 || bbPeriod > 100) errors.bbPeriod = 'Must be 5-100'
  if (bbStd < 1 || bbStd > 4) errors.bbStd = 'Must be 1.0-4.0'
  return errors
}

// ============================================================================
// Field Error Component
// ============================================================================

export function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <p className="text-xs text-destructive mt-1 flex items-center gap-1">
      {message}
    </p>
  )
}

// ============================================================================
// Slider Helper
// ============================================================================

export function sliderVal(v: number | readonly number[]): number {
  return Array.isArray(v) ? v[0] : v
}

// ============================================================================
// Context Type
// ============================================================================

interface SettingsContextValue {
  // Save status
  saveStatus: 'idle' | 'saving' | 'saved' | 'error'
  errorMessage: string | null
  isLoadingSettings: boolean

  // Handlers
  handleSave: () => Promise<void>
  handleReset: () => Promise<void>
  handleExport: () => void
  handleImport: () => void
  handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  handleConfirmImport: () => void

  // Import dialog state
  importConfirmOpen: boolean
  setImportConfirmOpen: (open: boolean) => void
  pendingImport: AppSettings | null
  setPendingImport: (settings: AppSettings | null) => void
  fileInputRef: React.RefObject<HTMLInputElement | null>

  // Validation
  validateAllTabs: () => ValidationErrors
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

// ============================================================================
// Provider
// ============================================================================

export function SettingsProvider({ children }: { children: ReactNode }) {
  // ---- Zustand store ----
  const {
    trendWeight, momentumWeight, volumeWeight, patternWeight,
    holdingDays, minScore, lookbackDays, slippagePct, commissionPct,
    vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays,
    maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
    macdFast, macdSlow, macdSignal, bbPeriod, bbStd,
    fromAppSettings, resetToDefaults,
  } = useSettingsStore()

  // ---- React Query hooks ----
  const { data: serverSettings, isLoading: isLoadingSettings } = useSettings()
  const updateMutation = useUpdateSettings()
  const resetMutation = useResetSettings()

  // ---- Local UI state ----
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [importConfirmOpen, setImportConfirmOpen] = useState(false)
  const [pendingImport, setPendingImport] = useState<AppSettings | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ---- Sync server settings into Zustand on first load ----
  useEffect(() => {
    if (serverSettings?.settings) {
      fromAppSettings(serverSettings.settings)
    }
  }, [serverSettings, fromAppSettings])

  // ---- Validate all tabs ----
  const validateAllTabs = useCallback((): ValidationErrors => {
    return {
      ...validateScoringWeights(trendWeight, momentumWeight, volumeWeight, patternWeight),
      ...validateBacktest(holdingDays, minScore, lookbackDays, slippagePct, commissionPct),
      ...validateOFFFilter(vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays),
      ...validateIndicators(
        maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
        macdFast, macdSlow, macdSignal, bbPeriod, bbStd
      ),
    }
  }, [
    trendWeight, momentumWeight, volumeWeight, patternWeight,
    holdingDays, minScore, lookbackDays, slippagePct, commissionPct,
    vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays,
    maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
    macdFast, macdSlow, macdSignal, bbPeriod, bbStd,
  ])

  // ---- Save handler ----
  const handleSave = async () => {
    const allErrors = validateAllTabs()
    if (Object.keys(allErrors).length > 0) {
      setSaveStatus('error')
      setErrorMessage('Please fix validation errors before saving')
      setTimeout(() => {
        setSaveStatus('idle')
        setErrorMessage(null)
      }, 3000)
      return
    }

    setSaveStatus('saving')
    setErrorMessage(null)

    try {
      const store = useSettingsStore.getState()
      const payload = store.toAppSettings()
      await updateMutation.mutateAsync(payload)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err: unknown) {
      setSaveStatus('error')
      const msg = err instanceof Error ? err.message : 'Failed to save settings'
      setErrorMessage(msg)
      setTimeout(() => {
        setSaveStatus('idle')
        setErrorMessage(null)
      }, 4000)
    }
  }

  // ---- Reset handler ----
  const handleReset = async () => {
    try {
      const response = await resetMutation.mutateAsync()
      if (response.settings) {
        fromAppSettings(response.settings)
      } else {
        resetToDefaults()
      }
    } catch {
      resetToDefaults()
    }
  }

  // ---- Export handler ----
  const handleExport = useCallback(() => {
    const store = useSettingsStore.getState()
    const payload = store.toAppSettings()
    const json = JSON.stringify(payload, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `trading-settings-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [])

  // ---- Import handler ----
  const handleImport = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  // ---- File change handler ----
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string) as AppSettings
        if (!data.markets || !data.data || !data.scoring || !data.backtest || !data.offFilter || !data.indicators) {
          setErrorMessage('Invalid settings file: missing required sections')
          setTimeout(() => setErrorMessage(null), 4000)
          return
        }
        setPendingImport(data)
        setImportConfirmOpen(true)
      } catch {
        setErrorMessage('Failed to parse settings file')
        setTimeout(() => setErrorMessage(null), 4000)
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }, [])

  // ---- Confirm import handler ----
  const handleConfirmImport = useCallback(() => {
    if (pendingImport) {
      fromAppSettings(pendingImport)
      setPendingImport(null)
      setImportConfirmOpen(false)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    }
  }, [pendingImport, fromAppSettings])

  const value: SettingsContextValue = {
    saveStatus,
    errorMessage,
    isLoadingSettings,
    handleSave,
    handleReset,
    handleExport,
    handleImport,
    handleFileChange,
    handleConfirmImport,
    importConfirmOpen,
    setImportConfirmOpen,
    pendingImport,
    setPendingImport,
    fileInputRef,
    validateAllTabs,
  }

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  )
}

// ============================================================================
// Hook
// ============================================================================

export function useSettingsContext() {
  const ctx = useContext(SettingsContext)
  if (!ctx) {
    throw new Error('useSettingsContext must be used within SettingsProvider')
  }
  return ctx
}
