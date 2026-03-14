import type { CourseWithRelations } from "@/lib/database.types"

interface IntensiveCoursesProps {
  /** Enrolled courses that have 集中 schedule entries */
  courses: CourseWithRelations[]
}

export function IntensiveCourses({ courses }: IntensiveCoursesProps) {
  return (
    <div className="flex h-full flex-col gap-2">
      <h3 className="px-1 text-sm font-semibold text-muted-foreground">
        集中科目
      </h3>
      <div className="flex flex-1 flex-col rounded-md border bg-card p-2">
        {courses.length === 0 ? (
          <div className="flex h-10 flex-1 items-center justify-center rounded-md border border-dashed border-muted-foreground/30 bg-transparent text-center text-xs text-muted-foreground sm:h-12 sm:text-sm">
            登録された集中科目はありません
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {courses.map((course) => {
              return (
                <div
                  key={course.id}
                  className="flex min-h-10 animate-in flex-col items-center justify-center rounded-md border border-transparent bg-secondary p-1 text-center text-xs text-secondary-foreground shadow-sm transition-colors zoom-in-95 fade-in hover:bg-secondary/80 sm:min-h-12 sm:p-2 sm:text-sm"
                >
                  <span className="line-clamp-2 md:line-clamp-3">
                    {course.name}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
