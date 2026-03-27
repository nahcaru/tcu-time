import { useState, useCallback, useMemo } from "react"
import { SearchBar } from "@/components/course/SearchBar"
import { FilterPanel, FilterContent } from "@/components/course/FilterPanel"
import { CourseCard } from "@/components/course/CourseCard"
import { CourseDialog } from "@/components/course/CourseDialog"
import { useCourses } from "@/hooks/use-courses"
import { useEnrollments } from "@/hooks/use-enrollments"
import { IconLoader2 } from "@tabler/icons-react"
import type { CourseWithRelations } from "@/lib/database.types"
import { PageHeader } from "@/components/layout/PageHeader"
import { usePageTutorial } from "@/hooks/use-page-tutorial"

export function CoursesPage() {
  // Tutorial
  usePageTutorial("courses")

  // Filter state
  const [selectedTargets, setSelectedTargets] = useState<string[]>([])
  const [selectedTerms, setSelectedTerms] = useState<string[]>([])
  const [search, setSearch] = useState("")
  const [enrolledOnly, setEnrolledOnly] = useState(false)
  const [freeSlotsOnly, setFreeSlotsOnly] = useState(false)
  const [advanceEnrollmentOnly, setAdvanceEnrollmentOnly] = useState(false)

  // Enrollments
  const { enrolledCourseIds, addEnrollment, removeEnrollment } =
    useEnrollments()

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

  // Dialog state
  const [dialogCourse, setDialogCourse] = useState<CourseWithRelations | null>(
    null
  )

  const handleToggleEnroll = useCallback(
    (courseId: string) => {
      if (enrolledCourseIds.has(courseId)) {
        removeEnrollment(courseId)
      } else {
        addEnrollment(courseId)
      }
    },
    [enrolledCourseIds, addEnrollment, removeEnrollment]
  )

  const suggestions = useMemo(() => {
    const items = new Set<string>()
    suggestionBase.forEach((c) => {
      items.add(c.name)
      c.instructors.forEach((i) => items.add(i))
    })
    return Array.from(items)
  }, [suggestionBase])

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
    <div className="relative flex min-h-full flex-col lg:h-full lg:overflow-hidden">
      <PageHeader title="科目一覧">
        <div className="flex w-full items-center gap-4">
          <div className="flex flex-1 justify-center">
            <SearchBar
              id="tutorial-search"
              value={search}
              onChange={setSearch}
              suggestions={suggestions}
            />
          </div>
          <div className="lg:hidden">
            <FilterPanel id="tutorial-filter-mobile" {...filterProps} />
          </div>
        </div>
      </PageHeader>

      <div className="flex min-h-0 flex-1 flex-col pt-14 md:flex-row md:pt-0">
        <div
          className="no-scrollbar hidden h-full w-64 shrink-0 overflow-y-auto border-r p-4 lg:block"
          id="tutorial-filter"
        >
          <h3 className="mb-2 font-semibold">フィルター</h3>
          <FilterContent {...filterProps} />
        </div>

        {/* Main Content Area */}
        <div
          className="min-w-0 flex-1 px-2 py-4 md:px-6 lg:overflow-y-auto"
          id="tutorial-course-list"
        >
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <IconLoader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="py-12 text-center text-destructive">
              データの取得に失敗しました: {error.message}
            </div>
          ) : courses.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              該当する科目が見つかりません
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="mb-1 text-sm text-muted-foreground">
                {courses.length}件の科目
              </div>
              {courses.map((course) => (
                <div
                  key={course.id}
                  onClick={() => setDialogCourse(course)}
                  className="cursor-pointer"
                >
                  <CourseCard
                    course={course}
                    isEnrolled={enrolledCourseIds.has(course.id)}
                    onToggleEnroll={() => handleToggleEnroll(course.id)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <CourseDialog
        open={dialogCourse !== null}
        onOpenChange={(open) => {
          if (!open) setDialogCourse(null)
        }}
        course={dialogCourse}
        isEnrolled={
          dialogCourse ? enrolledCourseIds.has(dialogCourse.id) : false
        }
        onToggleEnroll={
          dialogCourse ? () => handleToggleEnroll(dialogCourse.id) : undefined
        }
      />
    </div>
  )
}
