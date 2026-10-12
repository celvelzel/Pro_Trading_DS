import { memo, type ReactNode } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { CheckCircle, XCircle } from 'lucide-react'

interface StatusCardProps {
  title: ReactNode
  status: string
  isGood: boolean
  details?: string
  loading?: boolean
  className?: string
}

export const StatusCard = memo(function StatusCard({
  title,
  status,
  isGood,
  details,
  loading = false,
  className,
}: StatusCardProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="animate-pulse p-4">
          <div className="mb-2 h-4 w-32 rounded bg-muted" />
          <div className="mb-1.5 h-6 w-20 rounded bg-muted" />
          <div className="h-3.5 w-40 rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  const StatusIcon = isGood ? CheckCircle : XCircle

  return (
    <Card className={cn('transition-colors hover:border-primary/30', className)}>
      <CardContent className="p-4">
        <div className="mb-1.5 flex items-center gap-2 text-[13px] font-medium text-muted-foreground">
          {title}
        </div>
        <div className="flex items-center gap-2">
          <StatusIcon
            className={cn('size-5 shrink-0', isGood ? 'text-success' : 'text-error')}
          />
          <p className="truncate text-xl font-semibold tracking-tight text-foreground">
            {status}
          </p>
        </div>
        {details && (
          <p className="mt-1.5 line-clamp-2 text-[13px] leading-snug text-muted-foreground">
            {details}
          </p>
        )}
      </CardContent>
    </Card>
  )
})
