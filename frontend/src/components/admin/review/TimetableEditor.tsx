import {
  inferTerm,
  type RawCourse,
  type TimetableRawJson,
} from "@/lib/approvalService"
import { Badge } from "@/components/ui/badge"
import { ReviewItemCard } from "./ReviewItemCard"
import { AddButton } from "./FormControls"
import { CourseFieldsEditor } from "./CourseFieldsEditor"

interface TimetableEditorProps {
  raw: TimetableRawJson
  onChange: (r: TimetableRawJson) => void
  checkedSet: Set<number>
  onToggleCheck: (index: number, checked: boolean) => void
  extractionSemester?: string | null
  activeIndex?: number | null
  onSelectIndex?: (index: number) => void
  expandedSet?: Set<number>
  onToggleExpand?: (index: number) => void
}

export function TimetableEditor({
  raw,
  onChange,
  checkedSet,
  onToggleCheck,
  extractionSemester,
  activeIndex,
  onSelectIndex,
  expandedSet,
  onToggleExpand,
}: TimetableEditorProps) {
  const courses = raw.courses ?? []

  const updateCourse = (i: number, patch: Partial<RawCourse>) => {
    const next = [...courses]
    next[i] = { ...next[i], ...patch }
    onChange({ ...raw, courses: next, count: next.length })
  }

  const addCourse = () => {
    const defaultTerm = extractionSemester === "fall" ? "後期前" : "前期"
    onChange({
      ...raw,
      courses: [
        ...courses,
        {
          code: "",
          name: "",
          instructors: [""],
          term: defaultTerm,
          room: "",
          schedules: [],
          targets: [],
        },
      ],
      count: courses.length + 1,
    })
  }

  const removeCourse = (i: number) => {
    const next = courses.filter((_, idx) => idx !== i)
    onChange({ ...raw, courses: next, count: next.length })
  }

  const warningsByCode = (raw.validation_warnings ?? []).reduce<
    Record<string, typeof raw.validation_warnings>
  >((acc, w) => {
    const list = acc[w.code] ?? []
    list.push(w)
    acc[w.code] = list
    return acc
  }, {})

  return (
    <div className="space-y-3">
      {courses.map((c, i) => {
        const displayTerm = inferTerm(c, extractionSemester || raw.semester)
        const scheduleSummary = (c.schedules ?? [])
          .map((s) => `${s.day}${s.period}`)
          .join("・")
        const subtitle = [c.code, displayTerm, c.room, scheduleSummary]
          .filter(Boolean)
          .join(" / ")
        const courseWarnings = (c.code ? warningsByCode[c.code] : null) ?? []

        return (
          <ReviewItemCard
            key={i}
            checked={checkedSet.has(i)}
            onCheckedChange={(v) => onToggleCheck(i, v)}
            title={`#${i + 1} ${c.name || "（科目名なし）"}`}
            subtitle={subtitle}
            badges={
              <>
                {courseWarnings.length > 0 && (
                  <Badge
                    variant="outline"
                    className="h-4 px-1 text-[10px] font-normal border-amber-400 bg-amber-50 text-amber-800"
                  >
                    検知 {courseWarnings.length}件
                  </Badge>
                )}
                {displayTerm.includes("集中") && (
                  <Badge
                    variant="secondary"
                    className="h-4 px-1 text-[10px] font-normal"
                  >
                    集中講義
                  </Badge>
                )}
              </>
            }
            isActive={activeIndex === i}
            onClickHeader={() => onSelectIndex?.(i)}
            isOpen={expandedSet ? expandedSet.has(i) : undefined}
            onToggleOpen={onToggleExpand ? () => onToggleExpand(i) : undefined}
            onRemove={() => removeCourse(i)}
          >
            <CourseFieldsEditor
              course={c}
              onChange={(updated) => updateCourse(i, updated)}
              extractionSemester={extractionSemester || raw.semester}
              warnings={courseWarnings}
            />
          </ReviewItemCard>
        )
      })}
      <div className="pt-2">
        <AddButton onClick={addCourse} label="科目を新規追加" />
      </div>
    </div>
  )
}
