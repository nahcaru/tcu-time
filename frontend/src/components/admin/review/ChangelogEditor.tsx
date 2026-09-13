import {
  CHANGE_TYPES,
  VALID_DAYS,
  VALID_TERMS,
  VALID_PERIODS,
  type RawChange,
  type ChangelogRawJson,
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
        const subtitle = [
          c.course_code,
          c.term,
          c.day,
          c.period ? `${c.period}限` : "",
        ]
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
                <div className="grid grid-cols-2 gap-2">
                  <FormSelect
                    label="曜日"
                    value={c.day ?? ""}
                    options={["", ...VALID_DAYS]}
                    optionLabels={{ "": "指定なし" }}
                    onChange={(v) => updateChange(i, { day: v || null })}
                  />
                  <FormSelect
                    label="時限"
                    value={c.period != null ? String(c.period) : ""}
                    options={["", ...VALID_PERIODS.map(String)]}
                    optionLabels={{
                      "": "指定なし",
                      ...Object.fromEntries(
                        VALID_PERIODS.map((p) => [String(p), `${p}限`])
                      ),
                    }}
                    onChange={(v) =>
                      updateChange(i, {
                        period: v ? Number(v) || v : null,
                      })
                    }
                  />
                </div>
              </div>

              {/* Field changes (for update type) */}
              {c.change_type === "update" && (
                <div className="space-y-2">
                  <FormSectionHeader
                    title="変更項目"
                    count={(c.changes ?? []).length}
                  />
                  <div className="space-y-2">
                    {(c.changes ?? []).map((fc, fi) => (
                      <div
                        key={fi}
                        className="grid grid-cols-1 items-end gap-2 rounded-lg border bg-muted/20 p-2.5 sm:grid-cols-3"
                      >
                        <FormField
                          label="フィールド名"
                          value={fc.field}
                          placeholder="教室, 時間割など"
                          onChange={(v) => {
                            const fcs = [...(c.changes ?? [])]
                            fcs[fi] = { ...fcs[fi], field: v }
                            updateChange(i, { changes: fcs })
                          }}
                        />
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
                        <div className="flex items-end gap-1.5">
                          <FormField
                            label="変更後"
                            value={fc.new_value ?? ""}
                            placeholder="新データ"
                            onChange={(v) => {
                              const fcs = [...(c.changes ?? [])]
                              fcs[fi] = { ...fcs[fi], new_value: v || null }
                              updateChange(i, { changes: fcs })
                            }}
                            className="flex-1"
                          />
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
                      </div>
                    ))}
                  </div>
                  <AddButton
                    onClick={() => {
                      updateChange(i, {
                        changes: [
                          ...(c.changes ?? []),
                          { field: "", old_value: null, new_value: null },
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
