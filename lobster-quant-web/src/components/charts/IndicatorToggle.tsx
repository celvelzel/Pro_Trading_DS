'use client'

import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

export type IndicatorType = 'sma' | 'ema' | 'rsi' | 'macd' | 'bb'

interface IndicatorToggleProps {
  activeIndicators: IndicatorType[]
  onToggle: (indicator: IndicatorType) => void
  className?: string
}

const indicators: { type: IndicatorType; label: string; description: string }[] = [
  { type: 'sma', label: 'SMA', description: 'Simple Moving Average (20, 50, 200)' },
  { type: 'ema', label: 'EMA', description: 'Exponential Moving Average (12, 26)' },
  { type: 'rsi', label: 'RSI', description: 'Relative Strength Index (14)' },
  { type: 'macd', label: 'MACD', description: 'Moving Average Convergence Divergence' },
  { type: 'bb', label: 'BB', description: 'Bollinger Bands (20, 2)' },
]

export const IndicatorToggle = memo(function IndicatorToggle({
  activeIndicators,
  onToggle,
  className,
}: IndicatorToggleProps) {
  return (
    <div className={cn('flex items-center gap-2 flex-wrap', className)}>
      <span className="text-sm font-medium text-text-secondary mr-1">Indicators:</span>
      {indicators.map((ind) => {
        const isActive = activeIndicators.includes(ind.type)
        return (
          <Button
            key={ind.type}
            variant={isActive ? 'default' : 'outline'}
            size="sm"
            onClick={() => onToggle(ind.type)}
            title={ind.description}
            className={cn(
              'h-7 px-2 text-xs font-medium transition-colors',
              isActive && 'bg-primary text-primary-foreground'
            )}
          >
            {ind.label}
          </Button>
        )
      })}
    </div>
  )
})
