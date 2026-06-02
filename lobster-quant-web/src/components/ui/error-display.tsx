'use client'

import { memo, useMemo } from 'react'
import { AlertCircle, WifiOff, Lock, ServerCrash, Clock, SearchX, RefreshCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { ERROR_MESSAGES, categorizeError, ErrorCategory } from '@/lib/error-messages'

interface ErrorDisplayProps {
  /** The error object or message string */
  error?: any
  /** Explicitly set the error category */
  category?: ErrorCategory
  /** Language preference ('en' or 'zh') */
  lang?: 'en' | 'zh'
  /** Custom title (overrides default for category) */
  title?: string
  /** Custom message (overrides default for category) */
  message?: string
  /** Callback for retry action */
  onRetry?: () => void
  /** Label for retry button */
  retryLabel?: string
  /** Additional CSS classes for the container */
  className?: string
  /** Variant of the error display */
  variant?: 'card' | 'inline' | 'simple'
}

const CATEGORY_ICONS: Record<ErrorCategory, any> = {
  network: WifiOff,
  auth: Lock,
  api: ServerCrash,
  validation: SearchX,
  market: AlertCircle,
  timeout: Clock,
  unknown: AlertCircle,
}

export const ErrorDisplay = memo(function ErrorDisplay({
  error,
  category,
  lang = 'en',
  title,
  message,
  onRetry,
  retryLabel,
  className,
  variant = 'card',
}: ErrorDisplayProps) {
  const finalCategory = useMemo(() => {
    if (category) return category
    return categorizeError(error)
  }, [category, error])

  const defaultTexts = ERROR_MESSAGES[finalCategory]
  const Icon = CATEGORY_ICONS[finalCategory] || AlertCircle

  const displayTitle = title || defaultTexts.title[lang]
  const displayMessage = message || (typeof error === 'string' ? error : error?.message) || defaultTexts.message[lang]
  const displayRetryLabel = retryLabel || defaultTexts.action?.[lang] || (lang === 'en' ? 'Retry' : '重试')

  if (variant === 'simple') {
    return (
      <div className={cn('flex items-center gap-2 text-error', className)}>
        <Icon className="h-4 w-4 shrink-0" />
        <span className="text-sm font-medium">{displayMessage}</span>
        {onRetry && (
          <button 
            onClick={onRetry}
            className="text-xs underline hover:text-error/80 ml-2"
          >
            {displayRetryLabel}
          </button>
        )}
      </div>
    )
  }

  if (variant === 'inline') {
    return (
      <div className={cn('flex flex-col items-center p-4 text-center', className)}>
        <Icon className="h-8 w-8 text-error mb-2" />
        <h4 className="text-base font-semibold text-text-primary mb-1">{displayTitle}</h4>
        <p className="text-sm text-text-secondary mb-3">{displayMessage}</p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline" size="sm">
            <RefreshCcw className="w-3.5 h-3.5 mr-2" />
            {displayRetryLabel}
          </Button>
        )}
      </div>
    )
  }

  return (
    <Card className={cn('border-error/20 bg-error/5 overflow-hidden', className)}>
      <CardContent className="p-6">
        <div className="flex flex-col md:flex-row items-center md:items-start gap-4 text-center md:text-left">
          <div className="p-3 bg-error/10 rounded-full shrink-0">
            <Icon className="h-6 w-6 text-error" />
          </div>
          <div className="flex-1 space-y-1">
            <h3 className="text-lg font-semibold text-text-primary">
              {displayTitle}
            </h3>
            <p className="text-sm text-text-secondary">
              {displayMessage}
            </p>
          </div>
          {onRetry && (
            <div className="shrink-0 mt-2 md:mt-0">
              <Button onClick={onRetry} variant="default" className="bg-error hover:bg-error/90 text-white">
                <RefreshCcw className="w-4 h-4 mr-2" />
                {displayRetryLabel}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
})
