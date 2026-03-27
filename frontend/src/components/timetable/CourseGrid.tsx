import { useState, useMemo } from "react"
import type { CourseWithRelations } from "@/lib/database.types"
import { DAYS, PERIODS } from "@/lib/constants"
import { cn } from "@/lib/utils"
import { GridCell } from "./GridCell"
import { AddCourseDialog } from "./AddCourseDialog"
import { ConflictDialog } from "./ConflictDialog"
import { CourseDialog } from "@/components/course/CourseDialog"

interface CourseGridProps {
  title: string
  /** Terms to display in this grid (e.g. ["前期前"] for 前半, ["前期後"] for 後半) */
  terms: string[]
  /** All enrolled courses with relations */
  enrolledCourses: CourseWithRelations[]
  addEnrollment: (courseId: string) => Promise<void>
  removeEnrollment: (courseId: string) => Promise<void>
  enrolledCourseIds: Set<string>
}

export function CourseGrid({
  title,
  terms,
  enrolledCourses,
  addEnrollment,
  removeEnrollment,
  enrolledCourseIds,
}: CourseGridProps) {
  const [selectedSlot, setSelectedSlot] = useState<{
    day: string
    period: string
    state: "empty" | "single" | "conflict"
    courses: CourseWithRelations[]
  } | null>(null)

  // Build a lookup: day+period → courses for matching terms
  const grid = useMemo(() => {
    const map = new Map<string, CourseWithRelations[]>()

    for (const course of enrolledCourses) {
      if (!course.term || !terms.includes(course.term)) continue

      for (const schedule of course.schedules) {
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

  const handleToggleEnrollSingle = (courseId: string) => {
    if (enrolledCourseIds.has(courseId)) {
      removeEnrollment(courseId)
    } else {
      addEnrollment(courseId)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="px-1 text-sm font-semibold text-muted-foreground">
        {title}
      </h3>
      <div className="overflow-x-auto rounded-md border bg-card">
        <div className="grid grid-cols-[2rem_repeat(5,1fr)]">
          {/* Header Row */}
          <div className="border-r border-b bg-muted/30 p-2"></div>
          {DAYS.map((day) => (
            <div
              key={day}
              className={cn(
                "border-r border-b bg-muted/30 p-2 text-center text-sm font-medium",
                day === "金" && "border-r-0"
              )}
            >
              {day}
            </div>
          ))}

          {/* Grid Rows */}
          {PERIODS.map((period) => (
            <div key={period} className="contents">
              <div
                className={cn(
                  "flex items-center justify-center border-r border-b bg-muted/30 p-2 text-sm font-medium",
                  period === PERIODS[PERIODS.length - 1] && "border-b-0"
                )}
              >
                {period}
              </div>
              {DAYS.map((day) => {
                const courses = grid.get(`${day}-${period}`) ?? []
                let state: "empty" | "single" | "conflict" = "empty"
                let name = ""

                if (courses.length === 1) {
                  state = "single"
                  name = courses[0].name ?? ""
                } else if (courses.length > 1) {
                  state = "conflict"
                }

                return (
                  <div
                    key={`${day}-${period}`}
                    className={cn(
                      "border-r border-b bg-background p-1",
                      day === "金" && "border-r-0",
                      period === PERIODS[PERIODS.length - 1] && "border-b-0"
                    )}
                  >
                    <GridCell
                      state={state}
                      courseName={name}
                      onClick={() =>
                        setSelectedSlot({
                          day,
                          period: String(period),
                          state,
                          courses,
                        })
                      }
                    />
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Dialogs */}
      <AddCourseDialog
        open={selectedSlot?.state === "empty"}
        onOpenChange={(open) => !open && setSelectedSlot(null)}
        day={selectedSlot?.day ?? ""}
        period={selectedSlot?.period ?? ""}
        terms={terms}
        addEnrollment={addEnrollment}
        removeEnrollment={removeEnrollment}
        enrolledCourseIds={enrolledCourseIds}
      />

      {selectedSlot?.state === "single" && selectedSlot.courses.length > 0 && (
        <CourseDialog
          open={selectedSlot?.state === "single"}
          onOpenChange={(open) => !open && setSelectedSlot(null)}
          course={selectedSlot.courses[0]}
          isEnrolled={enrolledCourseIds.has(selectedSlot.courses[0].id)}
          onToggleEnroll={() =>
            handleToggleEnrollSingle(selectedSlot.courses[0].id)
          }
        />
      )}

      <ConflictDialog
        open={selectedSlot?.state === "conflict"}
        onOpenChange={(open) => !open && setSelectedSlot(null)}
        day={selectedSlot?.day ?? ""}
        period={selectedSlot?.period ?? ""}
        courses={selectedSlot?.courses ?? []}
        addEnrollment={addEnrollment}
        removeEnrollment={removeEnrollment}
        enrolledCourseIds={enrolledCourseIds}
      />
    </div>
  )
}
