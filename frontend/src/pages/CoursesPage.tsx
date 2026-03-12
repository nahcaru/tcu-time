import { useState, useCallback } from "react"
import { SearchBar } from "@/components/course/SearchBar"
import { FilterPanel } from "@/components/course/FilterPanel"
import { CourseCard } from "@/components/course/CourseCard"
import { CourseDialog } from "@/components/course/CourseDialog"
import { useCourses } from "@/hooks/use-courses"
import { useEnrollments } from "@/hooks/use-enrollments"
import { useIsMobile } from "@/hooks/use-mobile"
import { IconLoader2 } from "@tabler/icons-react"
import type { CourseWithRelations } from "@/lib/database.types"

export function CoursesPage() {
  const isMobile = useIsMobile()

  // Filter state
  const [selectedTargets, setSelectedTargets] = useState<string[]>([])
  const [selectedTerms, setSelectedTerms] = useState<string[]>([])
  const [search, setSearch] = useState("")
  const [enrolledOnly, setEnrolledOnly] = useState(false)

  // Enrollments
  const { enrolledCourseIds, addEnrollment, removeEnrollment } =
    useEnrollments()

  // Courses with filters
  const { courses, isLoading, error } = useCourses({
    targets: selectedTargets,
    terms: selectedTerms,
    search,
    enrolledOnly,
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

  const filterProps = {
    selectedTargets,
    selectedTerms,
    enrolledOnly,
    onTargetsChange: setSelectedTargets,
    onTermsChange: setSelectedTerms,
    onEnrolledOnlyChange: setEnrolledOnly,
  }

  return (
    <div className="flex h-full bg-background md:-mt-6 md:-mx-6 md:p-6 lg:p-0">
      {!isMobile && <FilterPanel {...filterProps} />}

      <div className="flex-1 flex flex-col min-w-0 lg:p-6 lg:pl-8">
        <div className="flex flex-col gap-4 mb-6">
          <div className="flex items-center gap-3">
            {isMobile && <FilterPanel {...filterProps} />}
            <SearchBar value={search} onChange={setSearch} />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <IconLoader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-12 text-destructive">
            データの取得に失敗しました: {error.message}
          </div>
        ) : courses.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            該当する科目が見つかりません
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="text-sm text-muted-foreground mb-1">
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

      <CourseDialog
        open={dialogCourse !== null}
        onOpenChange={(open) => {
          if (!open) setDialogCourse(null)
        }}
        course={dialogCourse}
        isEnrolled={dialogCourse ? enrolledCourseIds.has(dialogCourse.id) : false}
        onToggleEnroll={
          dialogCourse
            ? () => handleToggleEnroll(dialogCourse.id)
            : undefined
        }
      />
    </div>
  )
}
