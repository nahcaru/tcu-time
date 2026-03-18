import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog"
import { CourseCard } from "@/components/course/CourseCard"
import type { CourseWithRelations } from "@/lib/database.types"

interface ConflictDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  day: string
  period: string
  courses: CourseWithRelations[]
  addEnrollment: (courseId: string) => Promise<void>
  removeEnrollment: (courseId: string) => Promise<void>
  enrolledCourseIds: Set<string>
}

export function ConflictDialog({
  open,
  onOpenChange,
  day,
  period,
  courses,
  addEnrollment,
  removeEnrollment,
  enrolledCourseIds,
}: ConflictDialogProps) {
  // useEnrollments 削除

  const handleToggleEnroll = (courseId: string) => {
    if (enrolledCourseIds.has(courseId)) {
      removeEnrollment(courseId)
    } else {
      addEnrollment(courseId)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-hidden p-0 sm:max-w-xl">
        <DialogHeader className="border-b p-4">
          <DialogTitle className="text-lg">
            {day}曜 {period}限の重複科目
          </DialogTitle>
          <DialogDescription className="text-destructive">
            不要な科目の登録を解除して重複を解消してください。
          </DialogDescription>
        </DialogHeader>

        <div className="no-scrollbar flex flex-col gap-2 overflow-y-auto p-2">
          {courses.map((course) => (
            <CourseCard
              key={course.id}
              course={course}
              isEnrolled={enrolledCourseIds.has(course.id)}
              onToggleEnroll={() => handleToggleEnroll(course.id)}
            />
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
