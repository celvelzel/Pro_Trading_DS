import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { SignalType } from '@/lib/types'

interface SignalCardProps {
  signalType: SignalType
  score: number
  probability: number
  reasons: string[]
  loading?: boolean
  className?: string
}

const signalConfig = {
  bullish: {
    emoji: '🟢',
    label: 'Bullish Signal',
    bgColor: 'bg-success/10',
    borderColor: 'border-success',
    textColor: 'text-success',
  },
  bearish: {
    emoji: '🔴',
    label: 'Bearish Signal',
    bgColor: 'bg-error/10',
    borderColor: 'border-error',
    textColor: 'text-error',
  },
  neutral: {
    emoji: '🟡',
    label: 'Neutral Signal',
    bgColor: 'bg-warning/10',
    borderColor: 'border-warning',
    textColor: 'text-warning',
  },
}

export function SignalCard({
  signalType,
  score,
  probability,
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

  return (
    <Card className={cn('border-l-4', config.borderColor, className)}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">{config.emoji}</span>
          <h3 className={cn('font-semibold', config.textColor)}>
            {config.label}
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-sm text-text-secondary">Score</p>
            <p className="text-2xl font-bold text-text-primary">
              {score}
              <span className="text-sm font-normal text-text-tertiary">/100</span>
            </p>
          </div>
          <div>
            <p className="text-sm text-text-secondary">Probability</p>
            <p className="text-2xl font-bold text-text-primary">
              {probability}
              <span className="text-sm font-normal text-text-tertiary">%</span>
            </p>
          </div>
        </div>

        {reasons.length > 0 && (
          <div className="space-y-1">
            {reasons.map((reason, index) => (
              <p key={index} className="text-sm text-text-secondary">
                • {reason}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
