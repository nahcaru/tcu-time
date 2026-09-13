import { Skeleton } from "@/components/ui/skeleton"
import { TimeSlots } from "@/components/timetable/TimeSlots"
import { DAYS, PERIODS } from "@/lib/constants"

function GridSkeleton({ title }: { title: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">{title}</h3>
        <Skeleton className="h-4 w-12" />
      </div>
      <div className="overflow-hidden rounded-lg border bg-card shadow-sm">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="w-8 border-b border-r p-1 text-center text-xs font-normal text-muted-foreground" />
              {DAYS.map((day) => (
                <th
                  key={day}
                  className="border-b border-r p-1 text-center text-xs font-medium text-muted-foreground last:border-r-0"
                >
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PERIODS.map((period) => (
              <tr key={period}>
                <td className="border-b border-r p-1 text-center text-xs text-muted-foreground">
                  {period}
                </td>
                {DAYS.map((day) => (
                  <td
                    key={day}
                    className="h-14 border-b border-r p-1 last:border-r-0 sm:h-16"
                  >
                    <Skeleton className="h-full w-full rounded opacity-40" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function IntensiveSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-12" />
      </div>
      <div className="flex flex-col gap-2 rounded-lg border bg-card p-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    </div>
  )
}

function CreditsSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-5 w-28" />
      <div className="flex flex-col gap-3 rounded-lg border bg-card p-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
        <Skeleton className="h-6 w-full mt-2" />
      </div>
    </div>
  )
}

export function TimetableSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <TimeSlots />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <GridSkeleton title="前半" />
        <GridSkeleton title="後半" />
        <IntensiveSkeleton />
        <CreditsSkeleton />
      </div>
    </div>
  )
}
