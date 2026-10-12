'use client'

import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

export type Timeframe = '1d' | '1w' | '1m' | '3m' | '6m' | '1y' | '5y'

interface TimeframeSelectorProps {
  activeTimeframe: Timeframe
  onSelect: (timeframe: Timeframe) => void
  className?: string
}

const timeframes: { value: Timeframe; label: string }[] = [
  { value: '1d', label: '1D' },
  { value: '1w', label: '1W' },
  { value: '1m', label: '1M' },
  { value: '3m', label: '3M' },
  { value: '6m', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '5y', label: '5Y' },
]

export const TimeframeSelector = memo(function TimeframeSelector({
  activeTimeframe,
  onSelect,
  className,
}: TimeframeSelectorProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-0.5 rounded-lg border border-border bg-background p-0.5',
        className
      )}
    >
      {timeframes.map((tf) => {
        const isActive = activeTimeframe === tf.value
        return (
          <Button
            key={tf.value}
            variant="ghost"
            size="sm"
            onClick={() => onSelect(tf.value)}
            className={cn(
              'h-6 rounded-md px-2 text-xs font-medium transition-colors',
              isActive
                ? 'bg-muted text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {tf.label}
          </Button>
        )
      })}
    </div>
  )
})
