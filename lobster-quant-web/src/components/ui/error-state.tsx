import { memo } from 'react'
import { AlertCircle, RefreshCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  retryLabel?: string
  className?: string
}

export const ErrorState = memo(function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  retryLabel = 'Retry',
  className,
}: ErrorStateProps) {
  return (
    <Card className={cn('border-error/50', className)}>
      <CardContent className="p-6 text-center">
        <div className="flex justify-center mb-4">
          <div className="p-3 bg-error/10 rounded-full">
            <AlertCircle className="h-8 w-8 text-error" />
          </div>
        </div>
        <h3 className="text-lg font-semibold text-text-primary mb-2">{title}</h3>
        <p className="text-sm text-text-secondary mb-4">{message}</p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline">
            <RefreshCcw className="w-4 h-4 mr-2" />
            {retryLabel}
          </Button>
        )}
      </CardContent>
    </Card>
  )
})
