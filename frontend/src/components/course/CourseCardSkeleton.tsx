import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function CourseCardSkeleton() {
  return (
    <Card className="flex flex-row items-center justify-between gap-3 px-3.5 py-2.5 sm:gap-4 sm:p-4">
      <div className="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
        {/* Term & Slot */}
        <div className="flex flex-row flex-wrap items-center gap-1 sm:w-20 sm:shrink-0 sm:flex-col sm:items-start sm:gap-1.5 sm:pt-0.5">
          <Skeleton className="h-3.5 w-12 sm:h-4" />
          <Skeleton className="h-3.5 w-16 sm:h-4" />
        </div>

        {/* Title & Metadata */}
        <div className="min-w-0 flex-1 flex flex-col gap-1 sm:block sm:space-y-2">
          <Skeleton className="h-5 w-3/4 max-w-sm" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-3 w-24 sm:h-3.5" />
            <Skeleton className="h-3 w-12 sm:h-3.5" />
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
