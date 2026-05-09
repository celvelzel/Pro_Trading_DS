import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { CheckCircle, XCircle } from 'lucide-react'

interface StatusCardProps {
  title: string
  status: string
  isGood: boolean
  details?: string
  loading?: boolean
  className?: string
}

export function StatusCard({
  title,
  status,
  isGood,
  details,
  loading = false,
  className,
}: StatusCardProps) {
  if (loading) {
    return (
      <Card className={cn('animate-pulse', className)}>
        <CardContent className="p-4">
          <div className="h-6 bg-gray-200 rounded w-32 mb-2" />
          <div className="h-5 bg-gray-200 rounded w-20 mb-1" />
          <div className="h-3 bg-gray-200 rounded w-40" />
        </CardContent>
      </Card>
    )
  }

  const StatusIcon = isGood ? CheckCircle : XCircle
  const iconColor = isGood ? 'text-success' : 'text-error'

  return (
    <Card className={cn('', className)}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <StatusIcon className={cn('w-5 h-5', iconColor)} />
          <h3 className="font-semibold text-text-primary">{title}</h3>
        </div>
        <p className="text-lg font-medium text-text-primary">{status}</p>
        {details && (
          <p className="text-sm text-text-secondary mt-1">{details}</p>
        )}
      </CardContent>
    </Card>
  )
}
