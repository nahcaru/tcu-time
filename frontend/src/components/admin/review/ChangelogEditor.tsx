import {
  CHANGE_TYPES,
  VALID_TERMS,
  parseScheduleString,
  type RawChange,
  type ChangelogRawJson,
  type RawSchedule,
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
import { ScheduleEditor } from "./ScheduleEditor"
import { InstructorsEditor } from "./InstructorsEditor"
import { TargetsEditor } from "./TargetsEditor"
import { CourseFieldsEditor } from "./CourseFieldsEditor"

const CHANGE_TYPE_LABEL: Record<string, string> = {
  create: "新規",
  update: "更新",
  delete: "削除",
}

const CHANGE_TYPE_BADGE_STYLE: Record<string, string> = {
  create:
    "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  update: "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400",
  delete: "border-destructive/30 bg-destructive/10 text-destructive",
}

const COMMON_CHANGE_FIELDS = [
  "教室",
  "担当者",
  "曜日時限",
  "科目名",
  "学期",
  "受講対象",
  "備考",
  "講義コード",
  "クラス",
  "その他",
] as const

interface ChangelogEditorProps {
  raw: ChangelogRawJson
  onChange: (r: ChangelogRawJson) => void
  checkedSet: Set<number>
  onToggleCheck: (index: number, checked: boolean) => void
  activeIndex?: number | null
  onSelectIndex?: (index: number) => void
  expandedSet?: Set<number>
  onToggleExpand?: (index: number) => void
}

export function ChangelogEditor({
  raw,
  onChange,
  checkedSet,
  onToggleCheck,
  activeIndex,
  onSelectIndex,
  expandedSet,
  onToggleExpand,
}: ChangelogEditorProps) {
  const changes = raw.changes ?? []

  const updateChange = (i: number, patch: Partial<RawChange>) => {
    const next = [...changes]
    next[i] = { ...next[i], ...patch }
    onChange({ ...raw, changes: next, count: next.length })
  }

  const addChange = () => {
    onChange({
      ...raw,
      changes: [
        ...changes,
        {
          change_type: "update",
          course_code: "",
          course_name: "",
          changes: [{ field: "教室", old_value: null, new_value: null }],
        },
      ],
      count: changes.length + 1,
    })
  }

  const removeChange = (i: number) => {
    const next = changes.filter((_, idx) => idx !== i)
    onChange({ ...raw, changes: next, count: next.length })
  }

  return (
    <div className="space-y-3">
      {changes.map((c, i) => {
        const effectiveSchedules: RawSchedule[] =
          c.schedules && c.schedules.length > 0
            ? c.schedules
            : parseScheduleString(
                [c.day, c.period ? `${c.period}限` : ""]
                  .filter(Boolean)
                  .join(" ")
              )

        const changeSummary =
          c.change_type === "create"
            ? "新規科目"
            : c.change_type === "delete"
              ? "閉講・削除"
              : (c.changes ?? [])
                  .map((fc) => fc.field || "未指定")
                  .join(", ") || "変更内容なし"

        const subtitle = [c.course_code, changeSummary]
          .filter(Boolean)
          .join(" / ")

        return (
          <ReviewItemCard
            key={i}
            checked={checkedSet.has(i)}
            onCheckedChange={(v) => onToggleCheck(i, v)}
            title={`#${i + 1} ${c.course_name || "（科目名なし）"}`}
            subtitle={subtitle}
            badges={
              <Badge
                variant="outline"
                className={`h-4 px-1.5 text-[10px] font-normal ${
                  CHANGE_TYPE_BADGE_STYLE[c.change_type] ?? ""
                }`}
              >
                {CHANGE_TYPE_LABEL[c.change_type] ?? c.change_type}
              </Badge>
            }
            isActive={activeIndex === i}
            onClickHeader={() => onSelectIndex?.(i)}
            isOpen={expandedSet ? expandedSet.has(i) : undefined}
            onToggleOpen={onToggleExpand ? () => onToggleExpand(i) : undefined}
            onRemove={() => removeChange(i)}
          >
            <div className="space-y-4">
              {/* Change type selection */}
              <div className="w-48">
                <FormSelect
                  label="変更タイプ"
                  value={c.change_type}
                  options={CHANGE_TYPES}
                  optionLabels={CHANGE_TYPE_LABEL}
                  onChange={(v) =>
                    updateChange(i, {
                      change_type: v as RawChange["change_type"],
                    })
                  }
                />
              </div>

              {/* 1. 新規 (create): 時間割エディタと同じ CourseFieldsEditor を使い回し */}
              {c.change_type === "create" ? (
                <div className="space-y-2 rounded-lg border bg-muted/10 p-3">
                  <div className="text-xs font-semibold text-muted-foreground">
                    新規作成科目の詳細
                  </div>
                  <CourseFieldsEditor
                    course={{
                      code: c.course_code ?? "",
                      name: c.course_name ?? "",
                      term: c.term ?? undefined,
                      room: c.room ?? undefined,
                      instructors: c.instructors ?? [],
                      schedules: effectiveSchedules,
                      targets: c.targets ?? [],
                    }}
                    onChange={(updated) => {
                      updateChange(i, {
                        course_code: updated.code || null,
                        course_name: updated.name,
                        term: updated.term || null,
                        room: updated.room || null,
                        instructors: updated.instructors,
                        schedules: updated.schedules,
                        targets: updated.targets,
                        day:
                          updated.schedules?.map((s) => s.day).join(",") ||
                          null,
                        period: updated.schedules?.[0]?.period ?? null,
                      })
                    }}
                    extractionSemester={raw.semester}
                  />
                </div>
              ) : c.change_type === "delete" ? (
                /* 2. 削除 (delete): 削除対象の特定用フィールドのみ */
                <div className="space-y-3 rounded-lg border bg-destructive/5 p-3">
                  <div className="text-xs font-semibold text-destructive">
                    削除対象の科目（特定用）
                  </div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <FormField
                      label="講義コード"
                      value={c.course_code ?? ""}
                      placeholder="smba010011"
                      onChange={(v) =>
                        updateChange(i, { course_code: v || null })
                      }
                    />
                    <FormField
                      label="科目名"
                      value={c.course_name ?? ""}
                      placeholder="科目名"
                      onChange={(v) => updateChange(i, { course_name: v })}
                    />
                  </div>
                </div>
              ) : (
                /* 3. 更新 (update): 対象特定用コード/科目名 + 変更項目一覧 */
                <div className="space-y-4">
                  <div className="space-y-2 rounded-lg border bg-muted/10 p-3">
                    <div className="text-xs font-semibold text-muted-foreground">
                      更新対象の科目（特定用）
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <FormField
                        label="講義コード"
                        value={c.course_code ?? ""}
                        placeholder="smba010011"
                        onChange={(v) =>
                          updateChange(i, { course_code: v || null })
                        }
                      />
                      <FormField
                        label="科目名"
                        value={c.course_name ?? ""}
                        placeholder="科目名"
                        onChange={(v) => updateChange(i, { course_name: v })}
                      />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <FormSectionHeader
                      title="変更項目"
                      count={(c.changes ?? []).length}
                    />
                    <div className="space-y-2.5">
                      {(c.changes ?? []).map((fc, fi) => {
                        const options = Array.from(
                          new Set([
                            ...COMMON_CHANGE_FIELDS,
                            ...(fc.field ? [fc.field] : []),
                          ])
                        )

                        return (
                          <div
                            key={fi}
                            className="space-y-2.5 rounded-lg border bg-muted/20 p-3"
                          >
                            <div className="flex items-end justify-between gap-2">
                              <div className="w-48 shrink-0">
                                <FormSelect
                                  label="変更項目"
                                  value={
                                    COMMON_CHANGE_FIELDS.includes(
                                      fc.field as (typeof COMMON_CHANGE_FIELDS)[number]
                                    )
                                      ? fc.field
                                      : fc.field
                                        ? fc.field
                                        : "教室"
                                  }
                                  options={options}
                                  onChange={(v) => {
                                    const fcs = [...(c.changes ?? [])]
                                    fcs[fi] = {
                                      ...fcs[fi],
                                      field: v === "その他" ? "" : v,
                                    }
                                    updateChange(i, { changes: fcs })
                                  }}
                                />
                              </div>
                              {(!COMMON_CHANGE_FIELDS.includes(
                                fc.field as (typeof COMMON_CHANGE_FIELDS)[number]
                              ) ||
                                fc.field === "") && (
                                <FormField
                                  label="カスタム項目名"
                                  value={fc.field}
                                  placeholder="項目名を入力"
                                  onChange={(v) => {
                                    const fcs = [...(c.changes ?? [])]
                                    fcs[fi] = { ...fcs[fi], field: v }
                                    updateChange(i, { changes: fcs })
                                  }}
                                  className="flex-1"
                                />
                              )}
                              <DeleteButton
                                onClick={() => {
                                  updateChange(i, {
                                    changes: (c.changes ?? []).filter(
                                      (_, idx) => idx !== fi
                                    ),
                                  })
                                }}
                              />
                            </div>

                            {/* A案: 変更前は参考情報としてバッジ表示（非編集） */}
                            {fc.old_value && (
                              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                <span>変更前:</span>
                                <Badge
                                  variant="secondary"
                                  className="font-normal text-xs"
                                >
                                  {fc.old_value}
                                </Badge>
                              </div>
                            )}

                            {/* 変更後フォーム（共通コンポーネントを使用） */}
                            {fc.field === "曜日時限" ? (
                              <ScheduleEditor
                                label="変更後（曜日・時限）"
                                schedules={parseScheduleString(fc.new_value)}
                                onChange={(scheds) => {
                                  const text = scheds
                                    .map((s) => `${s.day}${s.period}`)
                                    .join(",")
                                  const fcs = [...(c.changes ?? [])]
                                  fcs[fi] = {
                                    ...fcs[fi],
                                    new_value: text || null,
                                  }
                                  updateChange(i, { changes: fcs })
                                }}
                              />
                            ) : fc.field === "担当者" ? (
                              <InstructorsEditor
                                label="変更後（担当教員）"
                                instructors={
                                  fc.new_value
                                    ? fc.new_value
                                        .split(/[,、]/)
                                        .map((s) => s.trim())
                                        .filter(Boolean)
                                    : []
                                }
                                onChange={(list) => {
                                  const fcs = [...(c.changes ?? [])]
                                  fcs[fi] = {
                                    ...fcs[fi],
                                    new_value:
                                      list.filter(Boolean).join(", ") || null,
                                  }
                                  updateChange(i, { changes: fcs })
                                }}
                              />
                            ) : fc.field === "受講対象" ? (
                              <TargetsEditor
                                label="変更後（受講対象）"
                                targets={
                                  fc.new_value
                                    ? fc.new_value
                                        .split(/[,、/]/)
                                        .map((s) => s.trim())
                                        .filter(Boolean)
                                        .map((name) => ({
                                          target_code: "",
                                          target_name: name,
                                          note: "",
                                        }))
                                    : []
                                }
                                onChange={(list) => {
                                  const fcs = [...(c.changes ?? [])]
                                  fcs[fi] = {
                                    ...fcs[fi],
                                    new_value:
                                      list
                                        .map(
                                          (t) =>
                                            t.target_name || t.target_code
                                        )
                                        .filter(Boolean)
                                        .join(", ") || null,
                                  }
                                  updateChange(i, { changes: fcs })
                                }}
                              />
                            ) : fc.field === "学期" ? (
                              <FormSelect
                                label="変更後（学期）"
                                value={fc.new_value ?? ""}
                                options={["", ...VALID_TERMS]}
                                optionLabels={{ "": "指定なし" }}
                                onChange={(v) => {
                                  const fcs = [...(c.changes ?? [])]
                                  fcs[fi] = {
                                    ...fcs[fi],
                                    new_value: v || null,
                                  }
                                  updateChange(i, { changes: fcs })
                                }}
                              />
                            ) : (
                              <FormField
                                label="変更後"
                                value={fc.new_value ?? ""}
                                placeholder="新データ"
                                onChange={(v) => {
                                  const fcs = [...(c.changes ?? [])]
                                  fcs[fi] = {
                                    ...fcs[fi],
                                    new_value: v || null,
                                  }
                                  updateChange(i, { changes: fcs })
                                }}
                              />
                            )}
                          </div>
                        )
                      })}
                    </div>
                    <AddButton
                      onClick={() => {
                        updateChange(i, {
                          changes: [
                            ...(c.changes ?? []),
                            {
                              field: "教室",
                              old_value: null,
                              new_value: null,
                            },
                          ],
                        })
                      }}
                      label="変更差分を追加"
                    />
                  </div>
                </div>
              )}
            </div>
          </ReviewItemCard>
        )
      })}
      <div className="pt-2">
        <AddButton onClick={addChange} label="変更レコードを追加" />
      </div>
    </div>
  )
}
