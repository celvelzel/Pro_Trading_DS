'use client'

import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Minus, TrendingUp, Flag, Trash2 } from 'lucide-react'
import type { AnnotationToolType } from './annotations'

interface AnnotationToolbarProps {
  activeTool: AnnotationToolType | null
  onSelectTool: (tool: AnnotationToolType | null) => void
  onClearAll: () => void
  annotationCount: number
  className?: string
}

const tools: { type: AnnotationToolType; label: string; icon: typeof Minus; description: string }[] = [
  {
    type: 'horizontal-line',
    label: 'H-Line',
    icon: Minus,
    description: 'Horizontal line at price level',
  },
  {
    type: 'trend-line',
    label: 'Trend',
    icon: TrendingUp,
    description: 'Trend line between two points',
  },
  {
    type: 'marker',
    label: 'Marker',
    icon: Flag,
    description: 'Price marker flag',
  },
]

export const AnnotationToolbar = memo(function AnnotationToolbar({
  activeTool,
  onSelectTool,
  onClearAll,
  annotationCount,
  className,
}: AnnotationToolbarProps) {
  return (
    <div className={cn('flex items-center gap-2 flex-wrap', className)}>
      <span className="text-sm font-medium text-text-secondary mr-1">Annotations:</span>
      {tools.map((tool) => {
        const isActive = activeTool === tool.type
        const Icon = tool.icon
        return (
          <Button
            key={tool.type}
            variant={isActive ? 'default' : 'outline'}
            size="sm"
            onClick={() => onSelectTool(isActive ? null : tool.type)}
            title={tool.description}
            className={cn(
              'h-7 px-2 text-xs font-medium transition-colors gap-1',
              isActive && 'bg-primary text-primary-foreground'
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {tool.label}
          </Button>
        )
      })}
      {annotationCount > 0 && (
        <Button
          variant="outline"
          size="sm"
          onClick={onClearAll}
          title="Clear all annotations"
          className="h-7 px-2 text-xs font-medium transition-colors gap-1 text-destructive hover:bg-destructive/10"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Clear All ({annotationCount})
        </Button>
      )}
    </div>
  )
})
