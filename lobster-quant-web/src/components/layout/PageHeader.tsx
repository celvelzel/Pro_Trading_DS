import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PageHeaderProps {
  title: string
  description?: string
  /** Right-aligned action area (buttons, selectors, status chips). */
  actions?: ReactNode
  className?: string
}

/**
 * Standard page heading: title + optional description on the left,
 * contextual actions on the right. Keeps a consistent vertical rhythm
 * across all pages.
 */
export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-start justify-between gap-x-4 gap-y-3',
        className
      )}
    >
      <div className="min-w-0 space-y-1">
        <h1 className="text-lg font-semibold leading-tight tracking-tight text-foreground">
          {title}
        </h1>
        {description && (
          <p className="max-w-2xl text-[13px] leading-snug text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      )}
    </div>
  )
}
