import { Card, CardContent, CardHeader } from '@/components/ui/card'

/**
 * Skeleton loader for the Backtest page.
 * Matches the layout: header, form (left), results (right).
 */
export function BacktestSkeleton() {
  return (
    <div className="container mx-auto py-8">
      {/* Page Header */}
      <div className="mb-8">
        <div className="h-8 bg-muted-foreground/20 rounded w-48 animate-pulse" />
        <div className="h-4 bg-muted-foreground/20 rounded w-64 mt-2 animate-pulse" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Form */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <div className="h-5 bg-muted-foreground/20 rounded w-32 animate-pulse" />
            </CardHeader>
            <CardContent className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 bg-muted-foreground/20 rounded w-20 animate-pulse" />
                  <div className="h-10 bg-muted-foreground/10 rounded animate-pulse" />
                </div>
              ))}
              <div className="h-10 bg-muted-foreground/20 rounded animate-pulse" />
            </CardContent>
          </Card>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Metrics */}
          <Card>
            <CardHeader>
              <div className="h-5 bg-muted-foreground/20 rounded w-40 animate-pulse" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="animate-pulse space-y-2">
                    <div className="h-4 bg-muted-foreground/20 rounded w-20" />
                    <div className="h-6 bg-muted-foreground/20 rounded w-16" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Equity Curve */}
          <Card>
            <CardHeader>
              <div className="h-5 bg-muted-foreground/20 rounded w-32 animate-pulse" />
            </CardHeader>
            <CardContent>
              <div className="h-[300px] bg-muted-foreground/10 rounded animate-pulse" />
            </CardContent>
          </Card>

          {/* Trades Table */}
          <Card>
            <CardHeader>
              <div className="h-5 bg-muted-foreground/20 rounded w-28 animate-pulse" />
            </CardHeader>
            <CardContent>
              <div className="animate-pulse space-y-3">
                {/* Table header */}
                <div className="grid grid-cols-6 gap-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-4 bg-muted-foreground/20 rounded" />
                  ))}
                </div>
                {/* Table rows */}
                {Array.from({ length: 5 }).map((_, row) => (
                  <div key={row} className="grid grid-cols-6 gap-4">
                    {Array.from({ length: 6 }).map((_, col) => (
                      <div key={col} className="h-4 bg-muted-foreground/10 rounded" />
                    ))}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
