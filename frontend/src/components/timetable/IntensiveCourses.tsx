import { useState } from "react"
import type { CourseWithRelations } from "@/lib/database.types"
import { GridCell } from "./GridCell"
import { AddCourseDialog } from "./AddCourseDialog"
import { CourseDialog } from "@/components/course/CourseDialog"

interface IntensiveCoursesProps {
  /** Enrolled courses that have 集中 or 通年 schedule entries */
  courses: CourseWithRelations[]
  /** Terms for the semester */
  terms: string[]
  addEnrollment: (courseId: string) => Promise<void>
  removeEnrollment: (courseId: string) => Promise<void>
  enrolledCourseIds: Set<string>
}

export function IntensiveCourses({
  courses,
  terms,
  addEnrollment,
  removeEnrollment,
  enrolledCourseIds,
}: IntensiveCoursesProps) {
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [selectedCourse, setSelectedCourse] =
    useState<CourseWithRelations | null>(null)

  const handleToggleEnrollSingle = async (courseId: string) => {
    if (enrolledCourseIds.has(courseId)) {
      await removeEnrollment(courseId)
    } else {
      await addEnrollment(courseId)
    }
  }

  return (
    <div className="flex h-full flex-col gap-2">
      <h3 className="px-1 text-sm font-semibold text-muted-foreground">
        集中・通年
      </h3>
      <div className="flex flex-1 flex-col rounded-md border bg-card p-2">
        <div className="flex flex-col gap-2">
          {courses.map((course) => (
            <GridCell
              key={course.id}
              state="single"
              courseName={course.name}
              onClick={() => setSelectedCourse(course)}
            />
          ))}

          <GridCell state="empty" onClick={() => setIsAddOpen(true)} />
        </div>
      </div>

      {/* Dialogs */}
      <AddCourseDialog
        open={isAddOpen}
        onOpenChange={setIsAddOpen}
        day="集中"
        period="集中"
        terms={terms}
        addEnrollment={addEnrollment}
        removeEnrollment={removeEnrollment}
        enrolledCourseIds={enrolledCourseIds}
      />

      {selectedCourse && (
        <CourseDialog
          open={!!selectedCourse}
          onOpenChange={(open) => !open && setSelectedCourse(null)}
          course={selectedCourse}
          isEnrolled={enrolledCourseIds.has(selectedCourse.id)}
          onToggleEnroll={() => handleToggleEnrollSingle(selectedCourse.id)}
        />
      )}
    </div>
  )
}
