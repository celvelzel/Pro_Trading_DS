'use client'

import { useState } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Settings, Save, RotateCcw } from 'lucide-react'

export default function SettingsPage() {
  const {
    enableUS,
    enableHK,
    enableA,
    dataYears,
    cacheTTL,
    trendWeight,
    momentumWeight,
    volumeWeight,
    patternWeight,
    setMarkets,
    setDataSettings,
    setScoringWeights,
    resetToDefaults,
  } = useSettingsStore()

  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

  const handleSave = () => {
    setSaveStatus('saving')
    // Settings are already saved via Zustand persist
    setTimeout(() => {
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    }, 500)
  }

  const handleReset = () => {
    resetToDefaults()
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Settings</h1>
          <p className="text-text-secondary mt-1">
            Configure your trading analysis preferences
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReset}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <Button onClick={handleSave} disabled={saveStatus === 'saving'}>
            {saveStatus === 'saving' ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Saving...
              </>
            ) : saveStatus === 'saved' ? (
              <>
                <Save className="w-4 h-4 mr-2" />
                Saved!
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market Settings */}
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
                onCheckedChange={(checked) =>
                  setMarkets({ enableUS: checked })
                }
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
                onCheckedChange={(checked) =>
                  setMarkets({ enableHK: checked })
                }
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
                onCheckedChange={(checked) =>
                  setMarkets({ enableA: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Data Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Data Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Data Years: {dataYears}
              </label>
              <Slider
                value={[dataYears]}
                onValueChange={(value) => {
                  const val = Array.isArray(value) ? value[0] : value
                  setDataSettings({ dataYears: val })
                }}
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
                onValueChange={(value) => {
                  const val = Array.isArray(value) ? value[0] : value
                  setDataSettings({ cacheTTL: val })
                }}
                min={60}
                max={3600}
                step={60}
                className="mt-2"
              />
              <p className="text-xs text-text-tertiary mt-1">
                How long to cache data before refreshing
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Scoring Weights */}
        <Card className="lg:col-span-2">
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
                  onValueChange={(value) => {
                    const val = Array.isArray(value) ? value[0] : value
                    setScoringWeights({ trend: val })
                  }}
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
                  onValueChange={(value) => {
                    const val = Array.isArray(value) ? value[0] : value
                    setScoringWeights({ momentum: val })
                  }}
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
                  onValueChange={(value) => {
                    const val = Array.isArray(value) ? value[0] : value
                    setScoringWeights({ volume: val })
                  }}
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
                  onValueChange={(value) => {
                    const val = Array.isArray(value) ? value[0] : value
                    setScoringWeights({ pattern: val })
                  }}
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
                <span className="font-medium text-text-primary">
                  {(trendWeight + momentumWeight + volumeWeight + patternWeight).toFixed(2)}
                </span>
                {Math.abs(trendWeight + momentumWeight + volumeWeight + patternWeight - 1) > 0.01 && (
                  <span className="text-warning ml-2">
                    (Should equal 1.00)
                  </span>
                )}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
