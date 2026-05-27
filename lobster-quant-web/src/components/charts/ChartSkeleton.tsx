interface ChartSkeletonProps {
  height?: number
  className?: string
}

export function ChartSkeleton({ height = 400, className }: ChartSkeletonProps) {
  return (
    <div 
      className={`animate-pulse rounded-lg bg-muted ${className}`}
      style={{ height }}
    >
      <div className="p-4 space-y-3">
        <div className="h-4 bg-muted-foreground/20 rounded w-1/4" />
        <div className="h-3 bg-muted-foreground/20 rounded w-1/2" />
        <div className="flex-1 mt-8">
          <div className="h-full bg-muted-foreground/10 rounded" />
        </div>
      </div>
    </div>
  )
}
