import { useMemo } from "react"
import { GridCell } from "./GridCell"
import { DAYS, PERIODS } from "@/lib/constants"
import type { CourseWithRelations } from "@/lib/database.types"

interface CourseGridProps {
  title: string
  /** Terms to display in this grid (e.g. ["前期前"] for 前半, ["前期後"] for 後半) */
  terms: string[]
  /** All enrolled courses with relations */
  enrolledCourses: CourseWithRelations[]
}

export function CourseGrid({ title, terms, enrolledCourses }: CourseGridProps) {
  // Build a lookup: day+period → courses for matching terms
  const grid = useMemo(() => {
    const map = new Map<string, CourseWithRelations[]>()

    for (const course of enrolledCourses) {
      for (const schedule of course.schedules) {
        if (!terms.includes(schedule.term)) continue
        const key = `${schedule.day}-${schedule.period}`
        const existing = map.get(key) ?? []
        // Avoid duplicates (same course, different schedule entries)
        if (!existing.some((c) => c.id === course.id)) {
          map.set(key, [...existing, course])
        }
      }
    }

    return map
  }, [enrolledCourses, terms])

  return (
    <div className="flex flex-col gap-2">
      <h3 className="px-1 text-sm font-semibold text-muted-foreground">
        {title}
      </h3>
      <div className="overflow-x-auto rounded-md border bg-card">
        <div className="grid min-w-[500px] grid-cols-[3rem_repeat(5,1fr)]">
          {/* Header Row */}
          <div className="border-r border-b bg-muted/30 p-2"></div>
          {DAYS.map((day) => (
            <div
              key={day}
              className="border-r border-b bg-muted/30 p-2 text-center text-sm font-medium last:border-r-0"
            >
              {day}
            </div>
          ))}

          {/* Grid Rows */}
          {PERIODS.map((period) => (
            <div key={period} className="contents">
              <div className="flex items-center justify-center border-r border-b bg-muted/30 p-2 text-sm font-medium last:border-b-0">
                {period}
              </div>
              {DAYS.map((day) => {
                const courses = grid.get(`${day}-${period}`) ?? []
                let state: "empty" | "single" | "conflict" = "empty"
                let name = ""

                if (courses.length === 1) {
                  state = "single"
                  name = courses[0].name
                } else if (courses.length > 1) {
                  state = "conflict"
                }

                return (
                  <div
                    key={`${day}-${period}`}
                    className="border-r border-b bg-background p-1 last:border-r-0 last:border-b-0"
                  >
                    <GridCell state={state} courseName={name} />
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
