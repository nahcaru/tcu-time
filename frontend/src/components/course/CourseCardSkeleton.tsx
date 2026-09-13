import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function CourseCardSkeleton() {
  return (
    <Card className="flex flex-row items-center justify-between gap-4 p-4">
      <div className="flex min-w-0 flex-1 flex-col sm:flex-row sm:items-center sm:gap-4">
        {/* Term & Slot */}
        <div className="mb-1.5 flex flex-row flex-wrap items-center gap-1 sm:mb-0 sm:w-20 sm:shrink-0 sm:flex-col sm:items-start sm:gap-1.5 sm:pt-0.5">
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-4 w-16" />
        </div>

        {/* Title & Metadata */}
        <div className="min-w-0 flex-1 space-y-2">
          <Skeleton className="h-5 w-3/4 max-w-sm" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-3.5 w-24" />
            <Skeleton className="h-3.5 w-12" />
          </div>
        </div>
      </div>

      {/* Button placeholder */}
      <div>
        <Skeleton className="h-9 w-9 rounded-full sm:h-9 sm:w-24" />
      </div>
    </Card>
  )
}
