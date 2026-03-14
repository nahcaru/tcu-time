import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { IconPlus, IconCheck } from "@tabler/icons-react"
import type { CourseWithRelations } from "@/lib/database.types"

interface CourseCardProps {
  course: CourseWithRelations
  isEnrolled: boolean
  onToggleEnroll?: () => void
  onClick?: () => void
}

export function CourseCard({
  course,
  isEnrolled,
  onToggleEnroll,
  onClick,
}: CourseCardProps) {
  // Build schedule summary: "前期後 月1・木1"
  const scheduleText = course.schedules
    .map((s) => `${s.day}${s.period}`)
    .join("・")
  const termText = [...new Set(course.schedules.map((s) => s.term))].join(", ")

  // Build target summary: "02機械"
  const targetText = course.course_targets
    .map((t) => `${t.target_code}${t.target_name}`)
    .join(", ")

  // Credits from metadata (pick first, they should be the same across curricula)
  const credits = course.course_metadata[0]?.credits

  return (
    <Card
      className="flex flex-col justify-between gap-4 p-4 transition-all hover:bg-accent/40 sm:flex-row sm:items-center"
      onClick={onClick}
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="text-xs font-medium text-muted-foreground">
          {termText} {scheduleText}
        </div>
        <span className="block truncate text-base font-semibold text-sidebar-primary">
          {course.name}
        </span>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="text-foreground">
            {course.instructors.join(", ")}
          </span>
          {targetText && <span>対象[{targetText}]</span>}
          {credits != null && <span>{credits}単位</span>}
        </div>
      </div>
      <div>
        <Button
          variant={isEnrolled ? "outline" : "default"}
          size="sm"
          className="w-full sm:w-auto"
          onClick={(e) => {
            e.stopPropagation()
            onToggleEnroll?.()
          }}
        >
          {isEnrolled ? (
            <IconCheck className="mr-1 h-4 w-4" />
          ) : (
            <IconPlus className="mr-1 h-4 w-4" />
          )}
          {isEnrolled ? "登録済み" : "登録する"}
        </Button>
      </div>
    </Card>
  )
}
