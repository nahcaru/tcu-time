import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { CourseWithRelations } from "@/lib/database.types"

interface IntensiveCoursesProps {
  /** Enrolled courses that have 集中 schedule entries */
  courses: CourseWithRelations[]
}

export function IntensiveCourses({ courses }: IntensiveCoursesProps) {
  return (
    <Card className="min-h-[248px] flex flex-col h-full">
      <CardHeader className="py-4">
        <CardTitle className="text-base font-semibold">
          集中科目
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-2">
        {courses.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            登録された集中科目はありません
          </div>
        ) : (
          courses.map((course) => {
            const terms = [
              ...new Set(course.schedules.map((s) => s.term)),
            ].join("・")
            return (
              <div
                key={course.id}
                className="rounded-md border p-3 text-sm bg-muted/40 fade-in zoom-in-95 animate-in"
              >
                <div className="font-semibold text-primary">{course.name}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {terms}
                </div>
              </div>
            )
          })
        )}
      </CardContent>
    </Card>
  )
}
