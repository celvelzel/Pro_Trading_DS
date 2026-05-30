import { Card, CardContent, CardHeader } from '@/components/ui/card'

/**
 * Skeleton loader for the Dashboard page.
 * Matches the layout: header, 3 status cards, chart, watchlist table.
 */
export function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-8 bg-muted-foreground/20 rounded w-48 animate-pulse" />
          <div className="h-4 bg-muted-foreground/20 rounded w-64 mt-2 animate-pulse" />
        </div>
        <div className="h-4 bg-muted-foreground/20 rounded w-32 animate-pulse" />
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-muted-foreground/20 rounded w-24" />
                <div className="h-8 bg-muted-foreground/20 rounded w-32" />
                <div className="h-3 bg-muted-foreground/20 rounded w-40" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="h-5 bg-muted-foreground/20 rounded w-36 animate-pulse" />
            <div className="flex gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-8 bg-muted-foreground/20 rounded w-12 animate-pulse" />
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] bg-muted-foreground/10 rounded animate-pulse" />
        </CardContent>
      </Card>

      {/* Watchlist Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="h-5 bg-muted-foreground/20 rounded w-24 animate-pulse" />
            <div className="h-8 bg-muted-foreground/20 rounded w-24 animate-pulse" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {/* Table header */}
            <div className="grid grid-cols-5 gap-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-4 bg-muted-foreground/20 rounded" />
              ))}
            </div>
            {/* Table rows */}
            {Array.from({ length: 5 }).map((_, row) => (
              <div key={row} className="grid grid-cols-5 gap-4">
                {Array.from({ length: 5 }).map((_, col) => (
                  <div key={col} className="h-4 bg-muted-foreground/10 rounded" />
                ))}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
