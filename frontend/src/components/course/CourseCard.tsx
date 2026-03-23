import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { IconPlus, IconCheck } from "@tabler/icons-react"
import type { CourseWithRelations } from "@/lib/database.types"
import { syllabusUrl } from "@/lib/constants"
import { useIsMobile } from "@/hooks/use-mobile"

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
  const isMobile = useIsMobile()

  // Build schedule summary: "前期後 月1・木1"
  const scheduleText = course.schedules
    .map((s) => `${s.day}${s.period}`)
    .join("・")
  const termText = course.term ?? ""

  // Credits from metadata (pick first, they should be the same across curricula)
  const credits = course.course_metadata[0]?.credits

  return (
    <Card
      className="flex flex-row items-center justify-between gap-4 p-4 transition-all hover:bg-accent/40"
      onClick={onClick}
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="text-sm font-medium text-muted-foreground">
          {termText} {scheduleText}
        </div>
        <a
          href={syllabusUrl(course.academic_year.toString(), course.code)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block max-w-full truncate text-lg font-semibold text-sidebar-primary hover:underline"
          onClick={(e) => {
            e.stopPropagation()
          }}
        >
          {course.name}
        </a>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span className="text-foreground">
            {course.instructors.length >= 3
              ? `${course.instructors[0]} 他`
              : course.instructors.join(", ")}
          </span>
          {credits != null && <span>{credits}単位</span>}
        </div>
      </div>
      <div>
        <Button
          variant={isEnrolled ? "outline" : "default"}
          size={isMobile ? "icon-lg" : "default"}
          className="rounded-full"
          onClick={(e) => {
            e.stopPropagation()
            onToggleEnroll?.()
          }}
        >
          {isEnrolled ? <IconCheck /> : <IconPlus />}
          {!isMobile && <span>{isEnrolled ? "登録済み" : "登録する"}</span>}
        </Button>
      </div>
    </Card>
  )
}
