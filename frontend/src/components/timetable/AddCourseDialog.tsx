import { useState, useMemo } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { SearchBar } from "@/components/course/SearchBar"
import { FilterPanel, FilterContent } from "@/components/course/FilterPanel"
import { CourseCard } from "@/components/course/CourseCard"
import { useCourses } from "@/hooks/use-courses"
import { IconLoader2 } from "@tabler/icons-react"

interface AddCourseDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  day: string
  period: string
  /** Terms from the grid context */
  terms: string[]
  addEnrollment: (courseId: string) => Promise<void>
  removeEnrollment: (courseId: string) => Promise<void>
  enrolledCourseIds: Set<string>
}

export function AddCourseDialog({
  open,
  onOpenChange,
  day,
  period,
  terms,
  addEnrollment,
  removeEnrollment,
  enrolledCourseIds,
}: AddCourseDialogProps) {
  // Filter state
  const [selectedTargets, setSelectedTargets] = useState<string[]>([])
  const [selectedTerms, setSelectedTerms] = useState<string[]>(terms)
  const [search, setSearch] = useState("")
  const [enrolledOnly, setEnrolledOnly] = useState(false)
  const [freeSlotsOnly, setFreeSlotsOnly] = useState(false)
  const [advanceEnrollmentOnly, setAdvanceEnrollmentOnly] = useState(false)

  // Enrollments は Props から受け取るため削除

  // Courses with filters
  const {
    courses,
    suggestionBase = [],
    isLoading,
    error,
  } = useCourses({
    targets: selectedTargets,
    terms: selectedTerms,
    search,
    enrolledOnly,
    freeSlotsOnly,
    advanceEnrollmentOnly,
    enrolledCourseIds,
  })

  // Filter by the specific slot
  const slotCourses = useMemo(() => {
    if (day === "集中") {
      return courses.filter((c) =>
        c.term != null && c.term.includes("集中")
      )
    }
    if (!day || !period) return []
    return courses.filter((c) =>
      c.schedules.some((s) => s.day === day && String(s.period) === period)
    )
  }, [courses, day, period])

  const suggestions = useMemo(() => {
    const items = new Set<string>()
    suggestionBase.forEach((c) => {
      items.add(c.name)
      c.instructors.forEach((i) => items.add(i))
    })
    return Array.from(items)
  }, [suggestionBase])

  const handleToggleEnroll = (courseId: string) => {
    if (enrolledCourseIds.has(courseId)) {
      removeEnrollment(courseId)
    } else {
      addEnrollment(courseId)
    }
  }

  const filterProps = {
    selectedTargets,
    selectedTerms,
    enrolledOnly,
    freeSlotsOnly,
    advanceEnrollmentOnly,
    onTargetsChange: setSelectedTargets,
    onTermsChange: setSelectedTerms,
    onEnrolledOnlyChange: setEnrolledOnly,
    onFreeSlotsOnlyChange: setFreeSlotsOnly,
    onAdvanceEnrollmentOnlyChange: setAdvanceEnrollmentOnly,
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[85vh] max-h-[85vh] flex-col overflow-hidden sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="text-lg">
            {day === "集中"
              ? "集中科目の登録"
              : `${day}曜 ${period}限の科目登録`}
          </DialogTitle>
        </DialogHeader>
        <div className="flex items-center gap-4">
          <div className="flex flex-1 justify-center">
            <SearchBar
              value={search}
              onChange={setSearch}
              suggestions={suggestions}
            />
          </div>
          <div className="lg:hidden">
            <FilterPanel {...filterProps} />
          </div>
        </div>

        <div className="flex min-h-0 flex-1 flex-row overflow-hidden">
          {/* Sidebar Filters - PCOnly */}
          <div className="no-scrollbar hidden border-r p-4 md:block md:w-60 md:shrink-0 md:overflow-y-auto">
            <h4 className="mb-2 text-xs font-semibold text-muted-foreground">
              フィルター
            </h4>
            <FilterContent {...filterProps} />
          </div>

          {/* Course List */}
          <div className="no-scrollbar flex-1 overflow-y-auto p-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <IconLoader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="py-12 text-center text-xs text-destructive">
                データの取得に失敗しました
              </div>
            ) : slotCourses.length === 0 ? (
              <div className="py-12 text-center text-xs text-muted-foreground">
                該当する科目が見つかりません
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <div className="mb-1 text-xs text-muted-foreground">
                  {slotCourses.length}件の科目
                </div>
                {slotCourses.map((course) => (
                  <CourseCard
                    key={course.id}
                    course={course}
                    isEnrolled={enrolledCourseIds.has(course.id)}
                    onToggleEnroll={() => handleToggleEnroll(course.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
