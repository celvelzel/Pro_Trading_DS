'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { useSettings, useUpdateSettings, useResetSettings } from '@/hooks/useSettings'
import type { AppSettings } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { HelpTooltip } from '@/components/ui/help-tooltip'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Settings,
  Save,
  RotateCcw,
  Globe,
  Database,
  BarChart3,
  FlaskConical,
  ShieldAlert,
  Activity,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Download,
  Upload,
} from 'lucide-react'

// ============================================================================
// Validation Helpers
// ============================================================================

interface ValidationErrors {
  [key: string]: string
}

function validateScoringWeights(
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

function validateBacktest(
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

function validateOFFFilter(
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

function validateIndicators(
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

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <p className="text-xs text-destructive mt-1 flex items-center gap-1">
      <AlertCircle className="w-3 h-3" />
      {message}
    </p>
  )
}

// ============================================================================
// Settings Page
// ============================================================================

export default function SettingsPage() {
  // ---- Zustand store ----
  const {
    enableUS, enableHK, enableA,
    dataYears, cacheTTL,
    trendWeight, momentumWeight, volumeWeight, patternWeight,
    holdingDays, minScore, lookbackDays, slippagePct, commissionPct,
    vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays,
    maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
    macdFast, macdSlow, macdSignal, bbPeriod, bbStd,
    benchmarkSymbol,
    setMarkets, setDataSettings, setScoringWeights,
    setBacktestSettings, setOFFFilter, setIndicators, setBenchmark,
    resetToDefaults, fromAppSettings,
  } = useSettingsStore()

  // ---- React Query hooks ----
  const { data: serverSettings, isLoading: isLoadingSettings } = useSettings()
  const updateMutation = useUpdateSettings()
  const resetMutation = useResetSettings()

  // ---- Local UI state ----
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('markets')
  const [importConfirmOpen, setImportConfirmOpen] = useState(false)
  const [pendingImport, setPendingImport] = useState<AppSettings | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ---- Sync server settings into Zustand on first load ----
  useEffect(() => {
    if (serverSettings?.settings) {
      fromAppSettings(serverSettings.settings)
    }
  }, [serverSettings, fromAppSettings])

  // ---- Validate current tab ----
  const validateCurrentTab = useCallback((): ValidationErrors => {
    switch (activeTab) {
      case 'scoring':
        return validateScoringWeights(trendWeight, momentumWeight, volumeWeight, patternWeight)
      case 'backtest':
        return validateBacktest(holdingDays, minScore, lookbackDays, slippagePct, commissionPct)
      case 'offFilter':
        return validateOFFFilter(vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays)
      case 'indicators':
        return validateIndicators(
          maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
          macdFast, macdSlow, macdSignal, bbPeriod, bbStd
        )
      default:
        return {}
    }
  }, [
    activeTab,
    trendWeight, momentumWeight, volumeWeight, patternWeight,
    holdingDays, minScore, lookbackDays, slippagePct, commissionPct,
    vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays,
    maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
    macdFast, macdSlow, macdSignal, bbPeriod, bbStd,
  ])

  // ---- Validate on tab change ----
  const validationErrors = useMemo(() => validateCurrentTab(), [validateCurrentTab])

  // ---- Save handler: PUT to /api/settings ----
  const handleSave = async () => {
    // Validate all tabs
    const allErrors: ValidationErrors = {
      ...validateScoringWeights(trendWeight, momentumWeight, volumeWeight, patternWeight),
      ...validateBacktest(holdingDays, minScore, lookbackDays, slippagePct, commissionPct),
      ...validateOFFFilter(vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays),
      ...validateIndicators(
        maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
        macdFast, macdSlow, macdSignal, bbPeriod, bbStd
      ),
    }

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

  // ---- Reset handler: POST to /api/settings/reset ----
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

  // ---- Export handler: download settings as JSON ----
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

  // ---- Import handler: trigger file input ----
  const handleImport = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  // ---- File change handler: parse JSON and show confirm dialog ----
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string) as AppSettings
        // Basic structure validation
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
    // Reset the input so the same file can be selected again
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

  // ---- Slider helper ----
  const sliderVal = (v: number | readonly number[]) => (Array.isArray(v) ? v[0] : v)

  // ---- Weight total ----
  const weightTotal = trendWeight + momentumWeight + volumeWeight + patternWeight

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
            <Settings className="w-8 h-8" />
            Settings
            <HelpTooltip helpKey="settings.title" />
          </h1>
          <p className="text-text-secondary mt-1">
            Configure your trading analysis preferences
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isLoadingSettings && (
            <span className="text-sm text-text-secondary flex items-center gap-1">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading...
            </span>
          )}
          {saveStatus === 'saved' && (
            <span className="text-sm text-success flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" />
              Saved!
            </span>
          )}
          {saveStatus === 'error' && errorMessage && (
            <span className="text-sm text-destructive flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {errorMessage}
            </span>
          )}
          <Button variant="outline" onClick={handleReset} disabled={resetMutation.isPending}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button variant="outline" onClick={handleImport}>
            <Upload className="w-4 h-4 mr-2" />
            Import
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button onClick={handleSave} disabled={saveStatus === 'saving' || isLoadingSettings}>
            {saveStatus === 'saving' ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Settings
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Tabbed Settings */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line" className="mb-6">
          <TabsTrigger value="markets">
            <Globe className="w-4 h-4 mr-1.5" />
            Markets
          </TabsTrigger>
          <TabsTrigger value="data">
            <Database className="w-4 h-4 mr-1.5" />
            Data
          </TabsTrigger>
          <TabsTrigger value="scoring">
            <BarChart3 className="w-4 h-4 mr-1.5" />
            Scoring
          </TabsTrigger>
          <TabsTrigger value="backtest">
            <FlaskConical className="w-4 h-4 mr-1.5" />
            Backtest
          </TabsTrigger>
          <TabsTrigger value="offFilter">
            <ShieldAlert className="w-4 h-4 mr-1.5" />
            OFF Filter
          </TabsTrigger>
          <TabsTrigger value="indicators">
            <Activity className="w-4 h-4 mr-1.5" />
            Indicators
          </TabsTrigger>
        </TabsList>

        {/* ================================================================== */}
        {/* MARKETS TAB                                                       */}
        {/* ================================================================== */}
        <TabsContent value="markets">
          <Card>
            <CardHeader>
              <CardTitle>Market Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-text-primary">US Stocks</p>
                  <p className="text-sm text-text-secondary">
                    US market stocks (NYSE, NASDAQ)
                  </p>
                </div>
                <Switch
                  checked={enableUS}
                  onCheckedChange={(checked) => setMarkets({ enableUS: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-text-primary">HK Stocks</p>
                  <p className="text-sm text-text-secondary">
                    Hong Kong market stocks
                  </p>
                </div>
                <Switch
                  checked={enableHK}
                  onCheckedChange={(checked) => setMarkets({ enableHK: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-text-primary">A-Shares</p>
                  <p className="text-sm text-text-secondary">
                    China A-share market
                  </p>
                </div>
                <Switch
                  checked={enableA}
                  onCheckedChange={(checked) => setMarkets({ enableA: checked })}
                />
              </div>
              <div className="pt-4 border-t border-border">
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Benchmark Symbol
                </label>
                <Input
                  type="text"
                  value={benchmarkSymbol}
                  onChange={(e) => setBenchmark(e.target.value.toUpperCase())}
                  placeholder="e.g., SPY"
                  className="max-w-xs"
                />
                <p className="text-xs text-text-tertiary mt-1">
                  Reference symbol for market comparison
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ================================================================== */}
        {/* DATA TAB                                                          */}
        {/* ================================================================== */}
        <TabsContent value="data">
          <Card>
            <CardHeader>
              <CardTitle>Data Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Data Years: {dataYears}
                </label>
                <Slider
                  value={[dataYears]}
                  onValueChange={(v) => setDataSettings({ dataYears: sliderVal(v) })}
                  min={1}
                  max={10}
                  step={1}
                  className="mt-2"
                />
                <p className="text-xs text-text-tertiary mt-1">
                  Number of years of historical data to fetch
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-text-secondary mb-2 block">
                  Cache TTL (seconds): {cacheTTL}
                </label>
                <Slider
                  value={[cacheTTL]}
                  onValueChange={(v) => setDataSettings({ cacheTTL: sliderVal(v) })}
                  min={300}
                  max={86400}
                  step={300}
                  className="mt-2"
                />
                <p className="text-xs text-text-tertiary mt-1">
                  How long to cache data before refreshing (300s – 86400s)
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ================================================================== */}
        {/* SCORING TAB                                                       */}
        {/* ================================================================== */}
        <TabsContent value="scoring">
          <Card>
            <CardHeader>
              <CardTitle>Scoring Weights</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Trend Weight: {trendWeight.toFixed(2)}
                  </label>
                  <Slider
                    value={[trendWeight]}
                    onValueChange={(v) => setScoringWeights({ trend: sliderVal(v) })}
                    min={0}
                    max={1}
                    step={0.05}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Weight for trend indicators (MA, MACD)
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Momentum Weight: {momentumWeight.toFixed(2)}
                  </label>
                  <Slider
                    value={[momentumWeight]}
                    onValueChange={(v) => setScoringWeights({ momentum: sliderVal(v) })}
                    min={0}
                    max={1}
                    step={0.05}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Weight for momentum indicators (RSI, Stochastic)
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Volume Weight: {volumeWeight.toFixed(2)}
                  </label>
                  <Slider
                    value={[volumeWeight]}
                    onValueChange={(v) => setScoringWeights({ volume: sliderVal(v) })}
                    min={0}
                    max={1}
                    step={0.05}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Weight for volume indicators
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Pattern Weight: {patternWeight.toFixed(2)}
                  </label>
                  <Slider
                    value={[patternWeight]}
                    onValueChange={(v) => setScoringWeights({ pattern: sliderVal(v) })}
                    min={0}
                    max={1}
                    step={0.05}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Weight for pattern recognition
                  </p>
                </div>
              </div>
              <div className="mt-4 p-3 bg-bg-card rounded-lg">
                <p className="text-sm text-text-secondary">
                  Total:{' '}
                  <span
                    className={`font-medium ${
                      Math.abs(weightTotal - 1) > 0.05 ? 'text-destructive' : 'text-success'
                    }`}
                  >
                    {weightTotal.toFixed(2)}
                  </span>
                  {Math.abs(weightTotal - 1) > 0.05 && (
                    <span className="text-warning ml-2">(Should equal 1.00)</span>
                  )}
                </p>
                <FieldError message={validationErrors.scoringTotal} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ================================================================== */}
        {/* BACKTEST TAB                                                      */}
        {/* ================================================================== */}
        <TabsContent value="backtest">
          <Card>
            <CardHeader>
              <CardTitle>Backtest Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Holding Days: {holdingDays}
                  </label>
                  <Slider
                    value={[holdingDays]}
                    onValueChange={(v) => setBacktestSettings({ holdingDays: sliderVal(v) })}
                    min={5}
                    max={100}
                    step={1}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Default holding period in days (5–100)
                  </p>
                  <FieldError message={validationErrors.holdingDays} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Min Score: {minScore}
                  </label>
                  <Slider
                    value={[minScore]}
                    onValueChange={(v) => setBacktestSettings({ minScore: sliderVal(v) })}
                    min={0}
                    max={100}
                    step={1}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Minimum score to enter a trade (0–100)
                  </p>
                  <FieldError message={validationErrors.minScore} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Lookback Days: {lookbackDays}
                  </label>
                  <Slider
                    value={[lookbackDays]}
                    onValueChange={(v) => setBacktestSettings({ lookbackDays: sliderVal(v) })}
                    min={100}
                    max={2000}
                    step={50}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Historical lookback window (100–2000)
                  </p>
                  <FieldError message={validationErrors.lookbackDays} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Slippage (%): {(slippagePct * 100).toFixed(2)}%
                  </label>
                  <Slider
                    value={[slippagePct]}
                    onValueChange={(v) => setBacktestSettings({ slippagePct: sliderVal(v) })}
                    min={0}
                    max={0.01}
                    step={0.0005}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Slippage per trade (0–1%)
                  </p>
                  <FieldError message={validationErrors.slippagePct} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Commission (%): {(commissionPct * 100).toFixed(2)}%
                  </label>
                  <Slider
                    value={[commissionPct]}
                    onValueChange={(v) => setBacktestSettings({ commissionPct: sliderVal(v) })}
                    min={0}
                    max={0.01}
                    step={0.0005}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Commission per trade (0–1%)
                  </p>
                  <FieldError message={validationErrors.commissionPct} />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ================================================================== */}
        {/* OFF FILTER TAB                                                    */}
        {/* ================================================================== */}
        <TabsContent value="offFilter">
          <Card>
            <CardHeader>
              <CardTitle>OFF (Risk-Off) Filter Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    VIX Threshold: {vixThreshold.toFixed(1)}
                  </label>
                  <Slider
                    value={[vixThreshold]}
                    onValueChange={(v) => setOFFFilter({ vixThreshold: sliderVal(v) })}
                    min={10}
                    max={100}
                    step={0.5}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    VIX level triggering risk-off signal (10–100)
                  </p>
                  <FieldError message={validationErrors.vixThreshold} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    ATR % Threshold: {(atrPctThreshold * 100).toFixed(1)}%
                  </label>
                  <Slider
                    value={[atrPctThreshold]}
                    onValueChange={(v) => setOFFFilter({ atrPctThreshold: sliderVal(v) })}
                    min={0.01}
                    max={0.2}
                    step={0.005}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    ATR percentage threshold (1–20%)
                  </p>
                  <FieldError message={validationErrors.atrPctThreshold} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Gap Threshold: {(gapThreshold * 100).toFixed(1)}%
                  </label>
                  <Slider
                    value={[gapThreshold]}
                    onValueChange={(v) => setOFFFilter({ gapThreshold: sliderVal(v) })}
                    min={0.01}
                    max={0.3}
                    step={0.005}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Gap percentage threshold (1–30%)
                  </p>
                  <FieldError message={validationErrors.gapThreshold} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    Min Volume Ratio: {minVolumeRatio.toFixed(2)}
                  </label>
                  <Slider
                    value={[minVolumeRatio]}
                    onValueChange={(v) => setOFFFilter({ minVolumeRatio: sliderVal(v) })}
                    min={0}
                    max={1}
                    step={0.01}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    Minimum volume ratio (0–1)
                  </p>
                  <FieldError message={validationErrors.minVolumeRatio} />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    MA200 Recovery Days: {ma200RecoveryDays}
                  </label>
                  <Slider
                    value={[ma200RecoveryDays]}
                    onValueChange={(v) => setOFFFilter({ ma200RecoveryDays: sliderVal(v) })}
                    min={10}
                    max={200}
                    step={5}
                    className="mt-2"
                  />
                  <p className="text-xs text-text-tertiary mt-1">
                    MA200 recovery lookback days (10–200)
                  </p>
                  <FieldError message={validationErrors.ma200RecoveryDays} />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ================================================================== */}
        {/* INDICATORS TAB                                                    */}
        {/* ================================================================== */}
        <TabsContent value="indicators">
          <Card>
            <CardHeader>
              <CardTitle>Technical Indicator Parameters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* MA Short */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    MA Short Period: {maShortPeriod}
                  </label>
                  <Slider
                    value={[maShortPeriod]}
                    onValueChange={(v) => setIndicators({ maShortPeriod: sliderVal(v) })}
                    min={5}
                    max={100}
                    step={1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.maShortPeriod} />
                </div>

                {/* MA Long */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    MA Long Period: {maLongPeriod}
                  </label>
                  <Slider
                    value={[maLongPeriod]}
                    onValueChange={(v) => setIndicators({ maLongPeriod: sliderVal(v) })}
                    min={50}
                    max={500}
                    step={5}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.maLongPeriod} />
                </div>

                {/* RSI Period */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    RSI Period: {rsiPeriod}
                  </label>
                  <Slider
                    value={[rsiPeriod]}
                    onValueChange={(v) => setIndicators({ rsiPeriod: sliderVal(v) })}
                    min={5}
                    max={50}
                    step={1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.rsiPeriod} />
                </div>

                {/* ATR Period */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    ATR Period: {atrPeriod}
                  </label>
                  <Slider
                    value={[atrPeriod]}
                    onValueChange={(v) => setIndicators({ atrPeriod: sliderVal(v) })}
                    min={5}
                    max={50}
                    step={1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.atrPeriod} />
                </div>

                {/* MACD Fast */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    MACD Fast: {macdFast}
                  </label>
                  <Slider
                    value={[macdFast]}
                    onValueChange={(v) => setIndicators({ macdFast: sliderVal(v) })}
                    min={5}
                    max={50}
                    step={1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.macdFast} />
                </div>

                {/* MACD Slow */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    MACD Slow: {macdSlow}
                  </label>
                  <Slider
                    value={[macdSlow]}
                    onValueChange={(v) => setIndicators({ macdSlow: sliderVal(v) })}
                    min={10}
                    max={100}
                    step={1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.macdSlow} />
                </div>

                {/* MACD Signal */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    MACD Signal: {macdSignal}
                  </label>
                  <Slider
                    value={[macdSignal]}
                    onValueChange={(v) => setIndicators({ macdSignal: sliderVal(v) })}
                    min={5}
                    max={50}
                    step={1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.macdSignal} />
                </div>

                {/* Bollinger Band Period */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    BB Period: {bbPeriod}
                  </label>
                  <Slider
                    value={[bbPeriod]}
                    onValueChange={(v) => setIndicators({ bbPeriod: sliderVal(v) })}
                    min={5}
                    max={100}
                    step={1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.bbPeriod} />
                </div>

                {/* Bollinger Band Std Dev */}
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">
                    BB Std Dev: {bbStd.toFixed(1)}
                  </label>
                  <Slider
                    value={[bbStd]}
                    onValueChange={(v) => setIndicators({ bbStd: sliderVal(v) })}
                    min={1}
                    max={4}
                    step={0.1}
                    className="mt-2"
                  />
                  <FieldError message={validationErrors.bbStd} />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Import Confirmation Dialog */}
      <AlertDialog open={importConfirmOpen} onOpenChange={setImportConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Import Settings</AlertDialogTitle>
            <AlertDialogDescription>
              This will overwrite your current settings with the imported values.
              You can save to the server afterwards if needed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setPendingImport(null)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmImport}>
              Import
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
