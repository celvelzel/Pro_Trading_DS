import { memo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
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
    barColor: 'bg-success',
    badgeVariant: 'success',
  },
  bearish: {
    icon: TrendingDown,
    label: 'Bearish Signal',
    bgColor: 'bg-error/10',
    borderColor: 'border-l-error',
    textColor: 'text-error',
    barColor: 'bg-error',
    badgeVariant: 'destructive',
  },
  neutral: {
    icon: Minus,
    label: 'Neutral Signal',
    bgColor: 'bg-warning/10',
    borderColor: 'border-l-warning',
    textColor: 'text-warning',
    barColor: 'bg-warning',
    badgeVariant: 'warning',
  },
} as const

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
      <Card className={className}>
        <CardContent className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Skeleton className="size-7 rounded-full" />
              <Skeleton className="h-5 w-28" />
            </div>
            <Skeleton className="h-5 w-14 rounded-md" />
          </div>
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <Skeleton className="mb-1 h-3 w-12" />
              <Skeleton className="mb-2 h-8 w-16" />
              <Skeleton className="h-1.5 w-full rounded-full" />
            </div>
            <div>
              <Skeleton className="mb-1 h-3 w-16" />
              <Skeleton className="h-8 w-16" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
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
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className={cn('rounded-full p-1.5', config.bgColor)}>
              <Icon className={cn('size-4', config.textColor)} />
            </div>
            <h3 className={cn('text-sm font-semibold', config.textColor)}>
              {config.label}
            </h3>
          </div>
          <Badge variant={config.badgeVariant} className="font-mono tabular-nums">
            {score}/100
          </Badge>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-4">
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Score</p>
            <div className="flex items-end gap-1">
              <p className="font-mono text-2xl font-bold tabular-nums text-foreground">
                {score}
              </p>
              <p className="mb-0.5 text-sm text-muted-foreground">/100</p>
            </div>
            {/* Score progress bar */}
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  config.barColor
                )}
                style={{ width: `${score}%` }}
              />
            </div>
          </div>
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Probability</p>
            <div className="flex items-end gap-1">
              <p className="font-mono text-2xl font-bold tabular-nums text-foreground">
                {probability}
              </p>
              <p className="mb-0.5 text-sm text-muted-foreground">%</p>
            </div>
          </div>
        </div>

        {reasons.length > 0 && (
          <div className="space-y-1.5 border-t border-border pt-2">
            {reasons.map((reason, index) => (
              <p
                key={index}
                className="flex items-start gap-1.5 text-sm text-muted-foreground"
              >
                <span className="mt-0.5 text-muted-foreground/60">•</span>
                {reason}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
})
