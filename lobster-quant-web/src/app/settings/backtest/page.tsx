'use client'

import { useMemo } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { Slider } from '@/components/ui/slider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FieldError, sliderVal, validateBacktest } from '../settings-context'

export default function BacktestPage() {
  const {
    holdingDays, minScore, lookbackDays, slippagePct, commissionPct,
    setBacktestSettings,
  } = useSettingsStore()

  const errors = useMemo(
    () => validateBacktest(holdingDays, minScore, lookbackDays, slippagePct, commissionPct),
    [holdingDays, minScore, lookbackDays, slippagePct, commissionPct]
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Backtest Parameters</CardTitle>
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
              Days to hold a position (5–100)
            </p>
            <FieldError message={errors.holdingDays} />
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
              step={5}
              className="mt-2"
            />
            <p className="text-xs text-text-tertiary mt-1">
              Minimum score to enter a trade (0–100)
            </p>
            <FieldError message={errors.minScore} />
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
            <FieldError message={errors.lookbackDays} />
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
            <FieldError message={errors.slippagePct} />
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
            <FieldError message={errors.commissionPct} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
