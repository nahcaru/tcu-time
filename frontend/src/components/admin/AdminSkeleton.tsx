import { Skeleton } from "@/components/ui/skeleton"

export function ExtractionTableSkeleton() {
  return (
    <div className="space-y-4">
      {/* Filter tabs skeleton */}
      <div className="flex gap-2 flex-wrap">
        <Skeleton className="h-8 w-20 rounded-full" />
        <Skeleton className="h-8 w-20 rounded-full" />
        <Skeleton className="h-8 w-20 rounded-full" />
        <Skeleton className="h-8 w-20 rounded-full" />
      </div>

      {/* Table skeleton */}
      <div className="rounded-xl border overflow-hidden bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">種別</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">学期</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">年度</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">PDF URL</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">ステータス</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">更新日時</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <tr key={i}>
                <td className="px-4 py-3.5"><Skeleton className="h-4 w-20" /></td>
                <td className="px-4 py-3.5"><Skeleton className="h-4 w-12" /></td>
                <td className="px-4 py-3.5"><Skeleton className="h-4 w-12" /></td>
                <td className="px-4 py-3.5"><Skeleton className="h-4 w-36" /></td>
                <td className="px-4 py-3.5"><Skeleton className="h-5 w-16 rounded-full" /></td>
                <td className="px-4 py-3.5"><Skeleton className="h-4 w-28" /></td>
                <td className="px-4 py-3.5"><Skeleton className="h-4 w-16" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function ReviewPageSkeleton() {
  return (
    <div className="flex flex-col gap-6 pt-6">
      {/* Header bar skeleton */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <Skeleton className="h-7 w-48" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24 rounded-md" />
          <Skeleton className="h-9 w-28 rounded-md" />
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Skeleton className="h-20 w-full rounded-xl" />
        <Skeleton className="h-20 w-full rounded-xl" />
        <Skeleton className="h-20 w-full rounded-xl" />
      </div>

      {/* Course items skeleton */}
      <div className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-xl" />
        ))}
      </div>
    </div>
  )
}
