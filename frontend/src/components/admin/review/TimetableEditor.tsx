import {
  inferTerm,
  VALID_DAYS,
  VALID_TERMS,
  VALID_PERIODS,
  type RawCourse,
  type TimetableRawJson,
} from "@/lib/approvalService"
import { Badge } from "@/components/ui/badge"
import { ReviewItemCard } from "./ReviewItemCard"
import {
  FormField,
  FormSelect,
  FormSectionHeader,
  AddButton,
  DeleteButton,
} from "./FormControls"
import { MultiTagInput } from "./MultiTagInput"

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

        return (
          <ReviewItemCard
            key={i}
            checked={checkedSet.has(i)}
            onCheckedChange={(v) => onToggleCheck(i, v)}
            title={`#${i + 1} ${c.name || "（科目名なし）"}`}
            subtitle={subtitle}
            badges={
              displayTerm.includes("集中") ? (
                <Badge
                  variant="secondary"
                  className="h-4 px-1 text-[10px] font-normal"
                >
                  集中講義
                </Badge>
              ) : undefined
            }
            isActive={activeIndex === i}
            onClickHeader={() => onSelectIndex?.(i)}
            isOpen={expandedSet ? expandedSet.has(i) : undefined}
            onToggleOpen={onToggleExpand ? () => onToggleExpand(i) : undefined}
            onRemove={() => removeCourse(i)}
          >
            {/* Basic fields */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <FormField
                label="講義コード"
                value={c.code}
                placeholder="smba010011"
                onChange={(v) => updateCourse(i, { code: v })}
              />
              <FormField
                label="科目名"
                value={c.name}
                placeholder="科目名"
                onChange={(v) => updateCourse(i, { name: v })}
              />
              <FormSelect
                label="学期"
                value={displayTerm}
                options={VALID_TERMS}
                onChange={(v) => updateCourse(i, { term: v })}
              />
              <FormField
                label="教室"
                value={c.room ?? ""}
                placeholder="13C など"
                onChange={(v) => updateCourse(i, { room: v })}
              />
              <FormField
                label="配当年次"
                value={c.year_level ?? 1}
                onChange={(v) =>
                  updateCourse(i, { year_level: Number(v) || 1 })
                }
              />
              <FormField
                label="クラス区分"
                value={c.class_section ?? ""}
                placeholder="A, B など"
                onChange={(v) => updateCourse(i, { class_section: v })}
              />
              <div className="sm:col-span-2">
                <FormField
                  label="備考"
                  value={c.notes ?? ""}
                  placeholder="特記事項があれば入力"
                  onChange={(v) => updateCourse(i, { notes: v })}
                />
              </div>
            </div>

            {/* Instructors */}
            <div className="space-y-2">
              <MultiTagInput
                label="担当教員"
                values={c.instructors ?? []}
                onChange={(vals) => updateCourse(i, { instructors: vals })}
                placeholder="教員名を入力して Enter（貼り付け可）"
              />
            </div>

            {/* Schedules */}
            <div className="space-y-2">
              <FormSectionHeader
                title="曜日・時限"
                count={(c.schedules ?? []).length}
              />
              <div className="space-y-1.5">
                {(c.schedules ?? []).map((s, si) => (
                  <div key={si} className="flex items-end gap-2">
                    <FormSelect
                      label="曜日"
                      value={s.day}
                      options={VALID_DAYS}
                      onChange={(v) => {
                        const sc = [...(c.schedules ?? [])]
                        sc[si] = { ...sc[si], day: v }
                        updateCourse(i, { schedules: sc })
                      }}
                      className="w-24 shrink-0"
                    />
                    <FormSelect
                      label="時限"
                      value={s.period}
                      options={VALID_PERIODS}
                      optionLabels={Object.fromEntries(
                        VALID_PERIODS.map((p) => [String(p), `${p}限`])
                      )}
                      onChange={(v) => {
                        const sc = [...(c.schedules ?? [])]
                        sc[si] = { ...sc[si], period: Number(v) || 1 }
                        updateCourse(i, { schedules: sc })
                      }}
                      className="w-24 shrink-0"
                    />
                    <DeleteButton
                      onClick={() => {
                        updateCourse(i, {
                          schedules: (c.schedules ?? []).filter(
                            (_, idx) => idx !== si
                          ),
                        })
                      }}
                    />
                  </div>
                ))}
              </div>
              <AddButton
                onClick={() => {
                  updateCourse(i, {
                    schedules: [
                      ...(c.schedules ?? []),
                      { day: "月", period: 1 },
                    ],
                  })
                }}
                label="コマを追加"
              />
            </div>

            {/* Targets */}
            <div className="space-y-2">
              <FormSectionHeader
                title="履修対象"
                count={(c.targets ?? []).length}
              />
              <div className="space-y-2">
                {(c.targets ?? []).map((t, ti) => (
                  <div
                    key={ti}
                    className="grid grid-cols-1 items-end gap-2 rounded-lg border bg-muted/20 p-2.5 sm:grid-cols-3"
                  >
                    <FormField
                      label="コード"
                      value={t.target_code}
                      placeholder="専修コード"
                      onChange={(v) => {
                        const tgt = [...(c.targets ?? [])]
                        tgt[ti] = { ...tgt[ti], target_code: v }
                        updateCourse(i, { targets: tgt })
                      }}
                    />
                    <FormField
                      label="名称"
                      value={t.target_name}
                      placeholder="専攻・コース名"
                      onChange={(v) => {
                        const tgt = [...(c.targets ?? [])]
                        tgt[ti] = { ...tgt[ti], target_name: v }
                        updateCourse(i, { targets: tgt })
                      }}
                    />
                    <div className="flex items-end gap-1.5">
                      <FormField
                        label="備考"
                        value={t.note ?? ""}
                        placeholder="備考"
                        onChange={(v) => {
                          const tgt = [...(c.targets ?? [])]
                          tgt[ti] = { ...tgt[ti], note: v }
                          updateCourse(i, { targets: tgt })
                        }}
                        className="flex-1"
                      />
                      <DeleteButton
                        onClick={() => {
                          updateCourse(i, {
                            targets: (c.targets ?? []).filter(
                              (_, idx) => idx !== ti
                            ),
                          })
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <AddButton
                onClick={() => {
                  updateCourse(i, {
                    targets: [
                      ...(c.targets ?? []),
                      { target_code: "", target_name: "", note: "" },
                    ],
                  })
                }}
                label="対象を追加"
              />
            </div>
          </ReviewItemCard>
        )
      })}
      <div className="pt-2">
        <AddButton onClick={addCourse} label="科目を新規追加" />
      </div>
    </div>
  )
}
