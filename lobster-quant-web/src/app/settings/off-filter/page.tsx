'use client'

import { useMemo } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { Slider } from '@/components/ui/slider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FieldError, sliderVal, validateOFFFilter } from '../settings-context'

export default function OffFilterPage() {
  const {
    vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays,
    setOFFFilter,
  } = useSettingsStore()

  const errors = useMemo(
    () => validateOFFFilter(vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays),
    [vixThreshold, atrPctThreshold, gapThreshold, minVolumeRatio, ma200RecoveryDays]
  )

  return (
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
            <FieldError message={errors.vixThreshold} />
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
            <FieldError message={errors.atrPctThreshold} />
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
            <FieldError message={errors.gapThreshold} />
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
              step={0.05}
              className="mt-2"
            />
            <p className="text-xs text-text-tertiary mt-1">
              Minimum volume ratio (0–1)
            </p>
            <FieldError message={errors.minVolumeRatio} />
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
              Days to recover above MA200 (10–200)
            </p>
            <FieldError message={errors.ma200RecoveryDays} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
