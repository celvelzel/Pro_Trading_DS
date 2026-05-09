import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: string
  delta?: string
  deltaType?: 'up' | 'down' | 'neutral'
  loading?: boolean
  className?: string
}

export function MetricCard({
  label,
  value,
  delta,
  deltaType = 'neutral',
  loading = false,
  className,
}: MetricCardProps) {
  if (loading) {
    return (
      <Card className={cn('animate-pulse', className)}>
        <CardContent className="p-4">
          <div className="h-4 bg-gray-200 rounded w-20 mb-2" />
          <div className="h-8 bg-gray-200 rounded w-24 mb-2" />
          <div className="h-3 bg-gray-200 rounded w-16" />
        </CardContent>
      </Card>
    )
  }

  const deltaColors = {
    up: 'text-success',
    down: 'text-error',
    neutral: 'text-text-tertiary',
  }

  const DeltaIcon = {
    up: TrendingUp,
    down: TrendingDown,
    neutral: Minus,
  }[deltaType]

  return (
    <Card className={cn('', className)}>
      <CardContent className="p-4">
        <p className="text-sm text-text-secondary mb-1">{label}</p>
        <p className="text-2xl font-semibold text-text-primary">{value}</p>
        {delta && (
          <div className={cn('flex items-center gap-1 mt-1', deltaColors[deltaType])}>
            <DeltaIcon className="w-3 h-3" />
            <span className="text-sm font-medium">{delta}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
