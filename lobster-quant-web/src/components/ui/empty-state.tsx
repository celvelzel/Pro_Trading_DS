import { memo, type ReactNode } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { Search, BarChart3, FlaskConical, Inbox } from 'lucide-react'

interface EmptyStateProps {
  icon?: 'search' | 'chart' | 'flask' | 'inbox'
  title: string
  message?: string
  action?: ReactNode
  className?: string
}

const iconMap = {
  search: Search,
  chart: BarChart3,
  flask: FlaskConical,
  inbox: Inbox,
}

export const EmptyState = memo(function EmptyState({
  icon = 'inbox',
  title,
  message,
  action,
  className,
}: EmptyStateProps) {
  const Icon = iconMap[icon]

  return (
    <Card className={className}>
      <CardContent className="p-8 text-center">
        <div className="flex justify-center mb-4">
          <div className="p-3 bg-muted rounded-full">
            <Icon className="h-8 w-8 text-muted-foreground" />
          </div>
        </div>
        <h3 className="text-lg font-semibold text-text-primary mb-2">{title}</h3>
        {message && (
          <p className="text-sm text-text-secondary mb-4">{message}</p>
        )}
        {action}
      </CardContent>
    </Card>
  )
})
