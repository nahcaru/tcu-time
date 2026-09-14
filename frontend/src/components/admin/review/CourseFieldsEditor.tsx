import {
  inferTerm,
  VALID_TERMS,
  type RawCourse,
} from "@/lib/approvalService"
import { FormField, FormSelect } from "./FormControls"
import { ScheduleEditor } from "./ScheduleEditor"
import { InstructorsEditor } from "./InstructorsEditor"
import { TargetsEditor } from "./TargetsEditor"

interface CourseFieldsEditorProps {
  course: RawCourse
  onChange: (course: RawCourse) => void
  extractionSemester?: string | null
  className?: string
}

export function CourseFieldsEditor({
  course: c,
  onChange,
  extractionSemester,
  className,
}: CourseFieldsEditorProps) {
  const displayTerm = c.term || inferTerm(c, extractionSemester)

  const update = (patch: Partial<RawCourse>) => {
    onChange({ ...c, ...patch })
  }

  return (
    <div className={className ?? "space-y-4"}>
      {/* Basic fields */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField
          label="講義コード"
          value={c.code}
          placeholder="smba010011"
          onChange={(v) => update({ code: v })}
        />
        <FormField
          label="科目名"
          value={c.name}
          placeholder="科目名"
          onChange={(v) => update({ name: v })}
        />
        <FormSelect
          label="学期"
          value={displayTerm}
          options={VALID_TERMS}
          onChange={(v) => update({ term: v })}
        />
        <FormField
          label="教室"
          value={c.room ?? ""}
          placeholder="13C など"
          onChange={(v) => update({ room: v })}
        />
        <FormField
          label="学年"
          value={c.year_level ?? 1}
          onChange={(v) => update({ year_level: Number(v) || 1 })}
        />
        <FormField
          label="クラス区分"
          value={c.class_section ?? ""}
          placeholder="A, B など"
          onChange={(v) => update({ class_section: v })}
        />
        <div className="sm:col-span-2">
          <FormField
            label="備考"
            value={c.notes ?? ""}
            placeholder="特記事項があれば入力"
            onChange={(v) => update({ notes: v })}
          />
        </div>
      </div>

      {/* Instructors */}
      <InstructorsEditor
        instructors={c.instructors ?? []}
        onChange={(instructors) => update({ instructors })}
      />

      {/* Schedules */}
      <ScheduleEditor
        schedules={c.schedules ?? []}
        onChange={(schedules) => update({ schedules })}
      />

      {/* Targets */}
      <TargetsEditor
        targets={c.targets ?? []}
        onChange={(targets) => update({ targets })}
      />
    </div>
  )
}
