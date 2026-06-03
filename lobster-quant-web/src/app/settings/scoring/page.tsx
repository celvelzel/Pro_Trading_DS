'use client'

import { useMemo } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { Slider } from '@/components/ui/slider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FieldError, sliderVal, validateScoringWeights, validateIndicators } from '../settings-context'

export default function ScoringPage() {
  const {
    trendWeight, momentumWeight, volumeWeight, patternWeight,
    setScoringWeights,
  } = useSettingsStore()

  const scoringErrors = useMemo(
    () => validateScoringWeights(trendWeight, momentumWeight, volumeWeight, patternWeight),
    [trendWeight, momentumWeight, volumeWeight, patternWeight]
  )

  return (
    <div className="space-y-6">
      {/* Scoring Weights */}
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
                min={0} max={1} step={0.05} className="mt-2"
              />
              <p className="text-xs text-text-tertiary mt-1">Weight for trend indicators (MA, MACD)</p>
            </div>
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Momentum Weight: {momentumWeight.toFixed(2)}
              </label>
              <Slider
                value={[momentumWeight]}
                onValueChange={(v) => setScoringWeights({ momentum: sliderVal(v) })}
                min={0} max={1} step={0.05} className="mt-2"
              />
              <p className="text-xs text-text-tertiary mt-1">Weight for momentum indicators (RSI, Stochastic)</p>
            </div>
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Volume Weight: {volumeWeight.toFixed(2)}
              </label>
              <Slider
                value={[volumeWeight]}
                onValueChange={(v) => setScoringWeights({ volume: sliderVal(v) })}
                min={0} max={1} step={0.05} className="mt-2"
              />
              <p className="text-xs text-text-tertiary mt-1">Weight for volume indicators</p>
            </div>
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                Pattern Weight: {patternWeight.toFixed(2)}
              </label>
              <Slider
                value={[patternWeight]}
                onValueChange={(v) => setScoringWeights({ pattern: sliderVal(v) })}
                min={0} max={1} step={0.05} className="mt-2"
              />
              <p className="text-xs text-text-tertiary mt-1">Weight for pattern recognition</p>
            </div>
          </div>
          <div className="mt-4 p-3 bg-muted rounded-md">
            <p className="text-sm text-text-secondary">
              Total: {(trendWeight + momentumWeight + volumeWeight + patternWeight).toFixed(2)} / 1.00
            </p>
            <FieldError message={scoringErrors.scoringTotal} />
          </div>
        </CardContent>
      </Card>

      {/* Technical Indicators */}
      <IndicatorsCard />
    </div>
  )
}

// ============================================================================
// Indicators Sub-Component
// ============================================================================

function IndicatorsCard() {
  const {
    maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod,
    macdFast, macdSlow, macdSignal, bbPeriod, bbStd,
    setIndicators,
  } = useSettingsStore()

  const errors = useMemo(
    () => validateIndicators(maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod, macdFast, macdSlow, macdSignal, bbPeriod, bbStd),
    [maShortPeriod, maLongPeriod, rsiPeriod, atrPeriod, macdFast, macdSlow, macdSignal, bbPeriod, bbStd]
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Technical Indicator Parameters</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <SliderField label={`MA Short: ${maShortPeriod}`} value={maShortPeriod} onChange={(v) => setIndicators({ maShortPeriod: v })} min={5} max={100} error={errors.maShortPeriod} />
          <SliderField label={`MA Long: ${maLongPeriod}`} value={maLongPeriod} onChange={(v) => setIndicators({ maLongPeriod: v })} min={50} max={500} step={5} error={errors.maLongPeriod} />
          <SliderField label={`RSI Period: ${rsiPeriod}`} value={rsiPeriod} onChange={(v) => setIndicators({ rsiPeriod: v })} min={5} max={50} error={errors.rsiPeriod} />
          <SliderField label={`ATR Period: ${atrPeriod}`} value={atrPeriod} onChange={(v) => setIndicators({ atrPeriod: v })} min={5} max={50} error={errors.atrPeriod} />
          <SliderField label={`MACD Fast: ${macdFast}`} value={macdFast} onChange={(v) => setIndicators({ macdFast: v })} min={5} max={50} error={errors.macdFast} />
          <SliderField label={`MACD Slow: ${macdSlow}`} value={macdSlow} onChange={(v) => setIndicators({ macdSlow: v })} min={10} max={100} error={errors.macdSlow} />
          <SliderField label={`MACD Signal: ${macdSignal}`} value={macdSignal} onChange={(v) => setIndicators({ macdSignal: v })} min={5} max={50} error={errors.macdSignal} />
          <SliderField label={`BB Period: ${bbPeriod}`} value={bbPeriod} onChange={(v) => setIndicators({ bbPeriod: v })} min={5} max={100} error={errors.bbPeriod} />
          <SliderField label={`BB Std Dev: ${bbStd.toFixed(1)}`} value={bbStd} onChange={(v) => setIndicators({ bbStd: v })} min={1} max={4} step={0.1} error={errors.bbStd} />
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Reusable Slider Field
// ============================================================================

function SliderField({ label, value, onChange, min, max, step = 1, error }: {
  label: string; value: number; onChange: (v: number) => void
  min: number; max: number; step?: number; error?: string
}) {
  return (
    <div>
      <label className="text-sm font-medium text-text-secondary mb-2 block">{label}</label>
      <Slider value={[value]} onValueChange={(v) => onChange(sliderVal(v))} min={min} max={max} step={step} className="mt-2" />
      <FieldError message={error} />
    </div>
  )
}
