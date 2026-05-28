'use client'

import { HelpCircle } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useHelpText } from '@/hooks/useHelpText'
import { cn } from '@/lib/utils'

interface HelpTooltipProps {
  /** Unique key to fetch help text from API */
  helpKey: string
  /** Optional custom trigger element */
  children?: React.ReactNode
  /** Additional CSS classes */
  className?: string
  /** Tooltip side position */
  side?: 'top' | 'right' | 'bottom' | 'left'
}

export function HelpTooltip({
  helpKey,
  children,
  className,
  side = 'top',
}: HelpTooltipProps) {
  const { data: helpText, isLoading } = useHelpText(helpKey)

  return (
    <Tooltip>
      <TooltipTrigger
        className={cn(
          'inline-flex items-center justify-center',
          'text-muted-foreground hover:text-foreground',
          'transition-colors duration-200',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          'rounded-full',
          className
        )}
        aria-label="Help"
      >
        {children || <HelpCircle className="h-4 w-4" />}
      </TooltipTrigger>
      <TooltipContent
        side={side}
        className="max-w-xs"
      >
        {isLoading ? (
          <span className="text-muted-foreground">Loading...</span>
        ) : helpText ? (
          <div className="space-y-1">
            {helpText.title && (
              <p className="font-semibold">{helpText.title}</p>
            )}
            <p className="text-xs leading-relaxed">{helpText.content}</p>
          </div>
        ) : (
          <span className="text-muted-foreground">No help available</span>
        )}
      </TooltipContent>
    </Tooltip>
  )
}
