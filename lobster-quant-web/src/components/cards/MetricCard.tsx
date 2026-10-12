import { memo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  label: React.ReactNode
  value: string
  delta?: string
  deltaType?: 'up' | 'down' | 'neutral'
  loading?: boolean
  className?: string
}

export const MetricCard = memo(function MetricCard({
  label,
  value,
  delta,
  deltaType = 'neutral',
  loading = false,
  className,
}: MetricCardProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="animate-pulse p-4">
          <div className="mb-2 h-3.5 w-20 rounded bg-muted" />
          <div className="mb-2 h-8 w-28 rounded bg-muted" />
          <div className="h-3.5 w-16 rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  const deltaColors = {
    up: 'text-success',
    down: 'text-error',
    neutral: 'text-muted-foreground',
  }

  const DeltaIcon = {
    up: TrendingUp,
    down: TrendingDown,
    neutral: Minus,
  }[deltaType]

  return (
    <Card className={cn('transition-colors hover:border-primary/30', className)}>
      <CardContent className="p-4">
        <div className="mb-1.5 text-[13px] font-medium text-muted-foreground">
          {label}
        </div>
        <div className="font-mono text-2xl font-semibold tracking-tight text-foreground">
          {value}
        </div>
        {delta && (
          <div
            className={cn(
              'mt-1.5 flex items-center gap-1 text-[13px] font-medium',
              deltaColors[deltaType]
            )}
          >
            <DeltaIcon className="size-3.5" />
            <span>{delta}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
})
