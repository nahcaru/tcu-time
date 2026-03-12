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
      className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-4 transition-all hover:bg-accent/40"
      onClick={onClick}
    >
      <div className="flex-1 space-y-1.5 min-w-0">
        <div className="text-xs text-muted-foreground font-medium">
          {termText} {scheduleText}
        </div>
        <span className="text-primary font-semibold block text-base truncate">
          {course.name}
        </span>
        <div className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
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
            <IconCheck className="w-4 h-4 mr-1" />
          ) : (
            <IconPlus className="w-4 h-4 mr-1" />
          )}
          {isEnrolled ? "登録済" : "登録"}
        </Button>
      </div>
    </Card>
  )
}
