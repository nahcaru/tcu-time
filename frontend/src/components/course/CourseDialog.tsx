import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { IconExternalLink } from "@tabler/icons-react"
import type { CourseWithRelations } from "@/lib/database.types"
import { syllabusUrl } from "@/lib/constants"

interface CourseDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  course: CourseWithRelations | null
  isEnrolled: boolean
  onToggleEnroll?: () => void
}

export function CourseDialog({
  open,
  onOpenChange,
  course,
  isEnrolled,
  onToggleEnroll,
}: CourseDialogProps) {
  if (!course) return null

  const scheduleText = course.schedules
    .map((s) => `${s.term} ${s.day}${s.period}`)
    .join(", ")

  const rooms = [
    ...new Set(course.schedules.map((s) => s.room).filter(Boolean)),
  ]

  const targetText = course.course_targets
    .map(
      (t) => `${t.target_code}${t.target_name}${t.note ? `(${t.note})` : ""}`
    )
    .join(", ")

  const credits = course.course_metadata[0]?.credits

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="text-xl">{course.name}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3 py-4 text-sm">
          <Row label="学期・時限" value={scheduleText} />
          <Row label="担当者" value={course.instructors.join(", ")} />
          {credits != null && <Row label="単位数" value={String(credits)} />}
          <Row label="講義コード" value={course.code} muted />
          {rooms.length > 0 && <Row label="教室" value={rooms.join(", ")} />}
          {targetText && <Row label="受講対象" value={targetText} />}
          {course.notes && <Row label="備考" value={course.notes} />}
          {course.class_section && (
            <Row label="クラス" value={course.class_section} />
          )}
        </div>
        <DialogFooter className="">
          <Button variant="outline" size="sm" asChild>
            <a
              href={syllabusUrl("2025", course.code)}
              target="_blank"
              rel="noopener noreferrer"
              className="gap-1"
            >
              <IconExternalLink className="h-4 w-4" />
              シラバス
            </a>
          </Button>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              閉じる
            </Button>
            <Button
              variant={isEnrolled ? "destructive" : "default"}
              onClick={onToggleEnroll}
            >
              {isEnrolled ? "登録取消" : "登録"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Row({
  label,
  value,
  muted,
}: {
  label: string
  value: string
  muted?: boolean
}) {
  return (
    <div className="grid grid-cols-3 items-baseline gap-2">
      <span className="font-medium text-muted-foreground">{label}</span>
      <span className={`col-span-2 ${muted ? "text-muted-foreground" : ""}`}>
        {value}
      </span>
    </div>
  )
}
