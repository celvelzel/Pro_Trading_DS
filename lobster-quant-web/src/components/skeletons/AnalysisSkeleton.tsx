import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

/**
 * Skeleton loader for the Analysis detail page.
 * Matches the layout: breadcrumb, price header, metrics, tabs with chart,
 * signal summary and radar.
 */
export function AnalysisSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-14" />
      </div>

      {/* Price Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1.5">
          <Skeleton className="h-7 w-32" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="space-y-1.5 md:text-right">
          <Skeleton className="h-8 w-36" />
          <Skeleton className="h-4 w-28 md:ml-auto" />
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="space-y-2">
                <Skeleton className="h-3.5 w-20" />
                <Skeleton className="h-8 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="space-y-4">
        <Skeleton className="h-8 w-full max-w-2xl rounded-lg" />

        {/* Chart */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <Skeleton className="h-5 w-32" />
              <div className="flex gap-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-7 w-12" />
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[400px] w-full" />
          </CardContent>
        </Card>

        {/* Signal summary + radar */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardContent className="p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Skeleton className="size-7 rounded-full" />
                    <Skeleton className="h-5 w-28" />
                  </div>
                  <Skeleton className="h-5 w-14 rounded-md" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent className="flex h-[300px] items-center justify-center">
              <Skeleton className="size-56 rounded-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
