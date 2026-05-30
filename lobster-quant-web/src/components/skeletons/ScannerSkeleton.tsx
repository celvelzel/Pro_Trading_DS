import { Card, CardContent, CardHeader } from '@/components/ui/card'

/**
 * Skeleton loader for the Scanner page.
 * Matches the layout: header, scan controls, results grid.
 */
export function ScannerSkeleton() {
  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <div className="h-8 bg-muted-foreground/20 rounded w-48 animate-pulse" />
        <div className="h-4 bg-muted-foreground/20 rounded w-72 mt-2 animate-pulse" />
      </div>

      {/* Scan Controls */}
      <Card>
        <CardHeader>
          <div className="h-5 bg-muted-foreground/20 rounded w-32 animate-pulse" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-muted-foreground/20 rounded w-16 animate-pulse" />
              <div className="h-10 bg-muted-foreground/10 rounded animate-pulse" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-muted-foreground/20 rounded w-24 animate-pulse" />
              <div className="h-10 bg-muted-foreground/10 rounded animate-pulse" />
            </div>
            <div className="flex items-end">
              <div className="h-10 bg-muted-foreground/20 rounded w-32 animate-pulse" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="animate-pulse space-y-3">
                <div className="flex items-center justify-between">
                  <div className="h-5 bg-muted-foreground/20 rounded w-20" />
                  <div className="h-6 bg-muted-foreground/20 rounded w-16" />
                </div>
                <div className="h-4 bg-muted-foreground/20 rounded w-32" />
                <div className="flex items-center justify-between">
                  <div className="h-6 bg-muted-foreground/20 rounded w-24" />
                  <div className="h-4 bg-muted-foreground/20 rounded w-16" />
                </div>
                <div className="flex gap-2">
                  <div className="h-5 bg-muted-foreground/10 rounded w-16" />
                  <div className="h-5 bg-muted-foreground/10 rounded w-20" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
