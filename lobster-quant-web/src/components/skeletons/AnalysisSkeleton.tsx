import { Card, CardContent, CardHeader } from '@/components/ui/card'

/**
 * Skeleton loader for the Analysis detail page.
 * Matches the layout: breadcrumb, header, tabs with chart and indicators.
 */
export function AnalysisSkeleton() {
  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <div className="h-4 bg-muted-foreground/20 rounded w-16 animate-pulse" />
        <div className="h-4 bg-muted-foreground/20 rounded w-4 animate-pulse" />
        <div className="h-4 bg-muted-foreground/20 rounded w-20 animate-pulse" />
      </div>

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-8 bg-muted-foreground/20 rounded w-32 animate-pulse" />
          <div className="h-4 bg-muted-foreground/20 rounded w-48 mt-2 animate-pulse" />
        </div>
        <div className="flex gap-2">
          <div className="h-6 bg-muted-foreground/20 rounded w-20 animate-pulse" />
          <div className="h-6 bg-muted-foreground/20 rounded w-24 animate-pulse" />
        </div>
      </div>

      {/* Price Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="animate-pulse space-y-2">
                <div className="h-4 bg-muted-foreground/20 rounded w-16" />
                <div className="h-6 bg-muted-foreground/20 rounded w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="space-y-4">
        <div className="flex gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-10 bg-muted-foreground/20 rounded w-24 animate-pulse" />
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

        {/* Indicators Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-muted-foreground/20 rounded w-20" />
                  <div className="h-6 bg-muted-foreground/20 rounded w-16" />
                  <div className="h-3 bg-muted-foreground/20 rounded w-32" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
