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
      <h3 className="font-semibold text-sm text-muted-foreground px-1">
        {title}
      </h3>
      <div className="rounded-md border overflow-x-auto bg-card">
        <div className="min-w-[500px] grid grid-cols-[3rem_repeat(6,1fr)]">
          {/* Header Row */}
          <div className="border-b border-r bg-muted/30 p-2"></div>
          {DAYS.map((day) => (
            <div
              key={day}
              className="border-b border-r last:border-r-0 bg-muted/30 p-2 text-center text-sm font-medium"
            >
              {day}
            </div>
          ))}

          {/* Grid Rows */}
          {PERIODS.map((period) => (
            <div key={period} className="contents">
              <div className="border-b last:border-b-0 border-r bg-muted/30 p-2 flex items-center justify-center text-sm font-medium">
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
                    className="border-b last:border-b-0 border-r last:border-r-0 p-1 bg-background"
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
