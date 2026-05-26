import { memo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { SignalType } from '@/lib/types'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface SignalCardProps {
  signalType: SignalType
  score: number
  probability?: number
  reasons: string[]
  loading?: boolean
  className?: string
}

const signalConfig = {
  bullish: {
    icon: TrendingUp,
    label: 'Bullish Signal',
    bgColor: 'bg-success/10',
    borderColor: 'border-l-success',
    textColor: 'text-success',
    badgeColor: 'bg-success/20 text-success',
  },
  bearish: {
    icon: TrendingDown,
    label: 'Bearish Signal',
    bgColor: 'bg-error/10',
    borderColor: 'border-l-error',
    textColor: 'text-error',
    badgeColor: 'bg-error/20 text-error',
  },
  neutral: {
    icon: Minus,
    label: 'Neutral Signal',
    bgColor: 'bg-warning/10',
    borderColor: 'border-l-warning',
    textColor: 'text-warning',
    badgeColor: 'bg-warning/20 text-warning',
  },
}

export const SignalCard = memo(function SignalCard({
  signalType,
  score,
  probability = 0,
  reasons,
  loading = false,
  className,
}: SignalCardProps) {
  if (loading) {
    return (
      <Card className={cn('animate-pulse', className)}>
        <CardContent className="p-4">
          <div className="h-6 bg-gray-200 rounded w-32 mb-4" />
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div className="h-3 bg-gray-200 rounded w-12 mb-1" />
              <div className="h-8 bg-gray-200 rounded w-16" />
            </div>
            <div>
              <div className="h-3 bg-gray-200 rounded w-16 mb-1" />
              <div className="h-8 bg-gray-200 rounded w-16" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="h-3 bg-gray-200 rounded w-full" />
            <div className="h-3 bg-gray-200 rounded w-3/4" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const config = signalConfig[signalType]
  const Icon = config.icon

  return (
    <Card className={cn('border-l-4', config.borderColor, className)}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className={cn('p-1.5 rounded-full', config.bgColor)}>
              <Icon className={cn('w-4 h-4', config.textColor)} />
            </div>
            <h3 className={cn('font-semibold', config.textColor)}>
              {config.label}
            </h3>
          </div>
          <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', config.badgeColor)}>
            {score}/100
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs text-text-secondary mb-1">Score</p>
            <div className="flex items-end gap-1">
              <p className="text-2xl font-bold text-text-primary">{score}</p>
              <p className="text-sm text-text-tertiary mb-0.5">/100</p>
            </div>
            {/* Score progress bar */}
            <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  signalType === 'bullish' && 'bg-success',
                  signalType === 'bearish' && 'bg-error',
                  signalType === 'neutral' && 'bg-warning'
                )}
                style={{ width: `${score}%` }}
              />
            </div>
          </div>
          <div>
            <p className="text-xs text-text-secondary mb-1">Probability</p>
            <div className="flex items-end gap-1">
              <p className="text-2xl font-bold text-text-primary">{probability}</p>
              <p className="text-sm text-text-tertiary mb-0.5">%</p>
            </div>
          </div>
        </div>

        {reasons.length > 0 && (
          <div className="space-y-1.5 pt-2 border-t">
            {reasons.map((reason, index) => (
              <p key={index} className="text-sm text-text-secondary flex items-start gap-1.5">
                <span className="text-text-tertiary mt-0.5">•</span>
                {reason}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
})
