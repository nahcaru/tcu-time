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
        { change_type: "update", course_name: "", changes: [] },
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
        // Resolve schedules list: either from c.schedules or parsed from day/period
        const effectiveSchedules: RawSchedule[] =
          c.schedules && c.schedules.length > 0
            ? c.schedules
            : parseScheduleString(
                [c.day, c.period ? `${c.period}限` : ""]
                  .filter(Boolean)
                  .join(" ")
              )

        const scheduleSummary =
          effectiveSchedules.length > 0
            ? effectiveSchedules.map((s) => `${s.day}${s.period}`).join("・")
            : [c.day, c.period ? `${c.period}限` : ""].filter(Boolean).join("")

        const subtitle = [c.course_code, c.term, scheduleSummary]
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
            <div className="space-y-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
                <FormField
                  label="科目コード"
                  value={c.course_code ?? ""}
                  placeholder="smba010011"
                  onChange={(v) => updateChange(i, { course_code: v || null })}
                />
                <div className="sm:col-span-2">
                  <FormField
                    label="科目名"
                    value={c.course_name ?? ""}
                    placeholder="科目名"
                    onChange={(v) => updateChange(i, { course_name: v })}
                  />
                </div>
                <FormSelect
                  label="学期"
                  value={c.term ?? ""}
                  options={["", ...VALID_TERMS]}
                  optionLabels={{ "": "指定なし" }}
                  onChange={(v) => updateChange(i, { term: v || null })}
                />
                {c.change_type === "create" && (
                  <div className="sm:col-span-2">
                    <ScheduleEditor
                      label="曜日・時限"
                      schedules={effectiveSchedules}
                      onChange={(newScheds) => {
                        const summaryDay = newScheds.map((s) => s.day).join(",")
                        const firstPeriod = newScheds[0]?.period ?? null
                        updateChange(i, {
                          schedules: newScheds,
                          day: summaryDay || null,
                          period: firstPeriod,
                        })
                      }}
                    />
                  </div>
                )}
              </div>

              {/* Extra fields for create type */}
              {c.change_type === "create" && (
                <div className="space-y-3 rounded-lg border bg-muted/10 p-3">
                  <div className="text-xs font-semibold text-muted-foreground">
                    新規科目の詳細情報
                  </div>
                  <FormField
                    label="教室"
                    value={c.room ?? ""}
                    placeholder="33G（横浜キャンパス）"
                    onChange={(v) => updateChange(i, { room: v || null })}
                  />
                  <FormField
                    label="担当教員"
                    value={(c.instructors ?? []).join(", ")}
                    placeholder="長沢 敬祐"
                    onChange={(v) =>
                      updateChange(i, {
                        instructors: v
                          .split(/[,、]/)
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                  <FormField
                    label="受講対象"
                    value={(c.targets ?? [])
                      .map((t) => t.target_name || t.target_code)
                      .join(", ")}
                    placeholder="00共通"
                    onChange={(v) =>
                      updateChange(i, {
                        targets: v
                          .split(/[,、]/)
                          .map((s) => s.trim())
                          .filter(Boolean)
                          .map((name) => ({
                            target_code: "",
                            target_name: name,
                          })),
                      })
                    }
                  />
                </div>
              )}

              {/* Field changes (for update type) */}
              {c.change_type === "update" && (
                <div className="space-y-2">
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
                          className="rounded-lg border bg-muted/20 p-3 space-y-2.5"
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
                                  fcs[fi] = { ...fcs[fi], field: v === "その他" ? "" : v }
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

                          {fc.field === "曜日時限" ? (
                            <div className="space-y-2 rounded-lg border bg-muted/20 p-3">
                              {fc.old_value && (
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                  <span>変更前:</span>
                                  <Badge variant="secondary" className="font-normal text-xs">
                                    {fc.old_value}
                                  </Badge>
                                </div>
                              )}
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
                            </div>
                          ) : (
                            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                              <FormField
                                label="変更前"
                                value={fc.old_value ?? ""}
                                placeholder="旧データ"
                                onChange={(v) => {
                                  const fcs = [...(c.changes ?? [])]
                                  fcs[fi] = { ...fcs[fi], old_value: v || null }
                                  updateChange(i, { changes: fcs })
                                }}
                              />
                              <FormField
                                label="変更後"
                                value={fc.new_value ?? ""}
                                placeholder="新データ"
                                onChange={(v) => {
                                  const fcs = [...(c.changes ?? [])]
                                  fcs[fi] = { ...fcs[fi], new_value: v || null }
                                  updateChange(i, { changes: fcs })
                                }}
                              />
                            </div>
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
                          { field: "教室", old_value: null, new_value: null },
                        ],
                      })
                    }}
                    label="変更差分を追加"
                  />
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
