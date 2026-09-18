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

  const isIntensiveOrFullYear = Boolean(
    course.term && (course.term.includes("集中") || course.term === "通年")
  )
  const displaySchedule =
    scheduleText || (isIntensiveOrFullYear ? "" : "時限未定")

  // Credits from metadata (pick first, they should be the same across curricula)
  const credits = course.course_metadata[0]?.credits

  return (
    <Card
      className="flex flex-row items-center justify-between gap-3 px-3.5 py-2.5 transition-all hover:bg-accent/40 sm:gap-4 sm:p-4"
      onClick={onClick}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
        {/* Mobile: inline text, Desktop: left column stacked */}
        <div className="flex flex-row flex-wrap items-center gap-x-1.5 text-xs font-medium leading-none text-muted-foreground sm:w-20 sm:shrink-0 sm:flex-col sm:items-start sm:gap-0.5 sm:pt-0.5 sm:text-sm sm:leading-normal">
          <span>{termText || "学期未定"}</span>
          {displaySchedule && <span>{displaySchedule}</span>}
        </div>

        {/* Right column (desktop) / Bottom part (mobile) */}
        <div className="min-w-0 flex-1 flex flex-col gap-1 sm:block sm:space-y-1">
          <a
            href={syllabusUrl(course.academic_year.toString(), course.code)}
            target="_blank"
            rel="noopener noreferrer"
            className="block max-w-full truncate text-base font-semibold leading-tight text-sidebar-primary hover:underline sm:inline-block sm:text-lg sm:leading-normal"
            onClick={(e) => {
              e.stopPropagation()
            }}
          >
            {course.name}
          </a>
          <div className="flex flex-wrap items-center gap-2 text-xs leading-none text-muted-foreground sm:leading-normal">
            <span className="text-foreground">
              {course.instructors.length >= 3
                ? `${course.instructors[0]} 他`
                : course.instructors.join(", ")}
            </span>
            {credits != null && <span>{credits}単位</span>}
          </div>
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
