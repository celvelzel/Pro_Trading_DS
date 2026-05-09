import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export function SkeletonCard() {
  return (
    <Card className="overflow-hidden border-none shadow-sm bg-card">
      <CardHeader className="p-4 pb-2">
        <Skeleton className="h-4 w-24 mb-1" />
        <Skeleton className="h-8 w-32" />
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        <Skeleton className="h-4 w-48" />
      </CardContent>
    </Card>
  )
}

export function ChartSkeleton() {
  return (
    <Card className="w-full h-[500px] border-none shadow-sm bg-card overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between p-4 border-b">
        <div className="flex gap-4">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-6 w-24" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-8 w-12" />
          <Skeleton className="h-8 w-12" />
          <Skeleton className="h-8 w-12" />
        </div>
      </CardHeader>
      <CardContent className="p-0 relative flex items-center justify-center h-[436px]">
        <div className="absolute inset-0 flex flex-col justify-between p-8 opacity-20">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex justify-between border-b border-muted py-8" />
          ))}
        </div>
        <Skeleton className="h-[300px] w-[80%] opacity-10" />
      </CardContent>
    </Card>
  )
}

export function SkeletonTable() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-8 w-32" />
      </div>
      <div className="rounded-md border">
        <div className="border-b px-4 py-3 bg-muted/50">
          <div className="grid grid-cols-4 gap-4">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
        <div className="p-4 space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="grid grid-cols-4 gap-4">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
