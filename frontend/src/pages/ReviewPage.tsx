import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router"
import { supabase } from "@/lib/supabase"
import type { Extraction } from "@/lib/database.types"
import {
  approveExtraction,
  VALID_DAYS,
  VALID_TERMS,
  VALID_PERIODS,
  CHANGE_TYPES,
  type RawCourse,
  type RawChange,
  type TimetableRawJson,
  type ChangelogRawJson,
  type AdvanceRawJson,
  type ExtractionRawJson,
} from "@/lib/approvalService"
import { PageHeader } from "@/components/layout/PageHeader"
import { IconChevronDown, IconChevronUp } from "@tabler/icons-react"

// =============================================================================
// Constants
// =============================================================================

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending:   { label: "処理中",   color: "bg-yellow-100 text-yellow-800" },
  extracted: { label: "承認待ち", color: "bg-blue-100 text-blue-800" },
  approved:  { label: "承認済み", color: "bg-green-100 text-green-800" },
}

const PDF_TYPE_LABELS: Record<string, string> = {
  timetable:          "授業時間表",
  changelog:          "変更一覧",
  advance_enrollment: "先行履修",
}

const CHANGE_TYPE_LABEL: Record<string, string> = {
  create: "新規", update: "更新", delete: "削除",
}

// =============================================================================
// Shared UI components
// =============================================================================

function Field({
  label,
  value,
  onChange,
  readOnly = false,
}: {
  label: string
  value: string | number
  onChange?: (v: string) => void
  readOnly?: boolean
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">{label}</span>
      {readOnly ? (
        <span className="text-sm">{value}</span>
      ) : (
        <input
          className="text-sm border rounded px-1.5 py-0.5 bg-background focus:outline-none focus:ring-1 focus:ring-primary w-full min-w-0"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
        />
      )}
    </div>
  )
}

function SelectField({
  label,
  value,
  options,
  optionLabels,
  onChange,
}: {
  label: string
  value: string | number
  options: readonly (string | number)[]
  optionLabels?: Record<string, string>
  onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">{label}</span>
      <select
        className="text-sm border rounded px-1.5 py-0.5 bg-background focus:outline-none focus:ring-1 focus:ring-primary"
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={String(opt)} value={String(opt)}>
            {optionLabels?.[String(opt)] ?? opt}
          </option>
        ))}
      </select>
    </div>
  )
}

function AddRowButton({ onClick, label = "+ 行を追加" }: { onClick: () => void; label?: string }) {
  return (
    <button type="button" onClick={onClick} className="text-xs text-primary hover:underline mt-1">
      {label}
    </button>
  )
}

function RemoveButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="text-xs text-destructive hover:underline shrink-0">
      削除
    </button>
  )
}

function CheckboxRow({
  checked,
  onChange,
  title,
  description,
  children,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  title?: string
  description?: string
  children: React.ReactNode
}) {
  const [isOpen, setIsOpen] = useState(!checked)
  const [prevChecked, setPrevChecked] = useState(checked)

  if (checked !== prevChecked) {
    setPrevChecked(checked)
    setIsOpen(!checked)
  }

  return (
    <div className="flex gap-3 items-start transition-all">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-3.5 h-4 w-4 shrink-0 accent-primary cursor-pointer"
      />
      <div className="flex-1 min-w-0 rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden">
        {/* Toggle header */}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center justify-between w-full p-3 text-left hover:bg-muted/50 transition-colors"
        >
          <div className="flex flex-col gap-0.5 pr-2">
            <span className="text-sm font-semibold">{title || "詳細情報"}</span>
            {description && <span className="text-xs text-muted-foreground truncate">{description}</span>}
          </div>
          {isOpen ? (
            <IconChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <IconChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
        </button>

        {/* Content */}
        {isOpen && (
          <div className="p-3 border-t bg-background/50">
            {children}
          </div>
        )}
      </div>
    </div>
  )
}

function SimpleCheckboxRow({
  checked,
  onChange,
  children,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  children: React.ReactNode
}) {
  return (
    <div className="flex gap-2 items-center">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 shrink-0 accent-primary cursor-pointer"
      />
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
}

// =============================================================================
// Timetable editor
// =============================================================================

function TimetableEditor({
  raw,
  onChange,
  checkedSet,
  onToggleCheck,
}: {
  raw: TimetableRawJson
  onChange: (r: TimetableRawJson) => void
  checkedSet: Set<number>
  onToggleCheck: (index: number, checked: boolean) => void
}) {
  const courses = raw.courses ?? []

  const updateCourse = (i: number, patch: Partial<RawCourse>) => {
    const next = [...courses]
    next[i] = { ...next[i], ...patch }
    onChange({ ...raw, courses: next, count: next.length })
  }

  const addCourse = () => {
    onChange({
      ...raw,
      courses: [
        ...courses,
        { code: "", name: "", instructors: [""], term: "前期", room: "", schedules: [], targets: [] },
      ],
      count: courses.length + 1,
    })
  }

  const removeCourse = (i: number) => {
    const next = courses.filter((_, idx) => idx !== i)
    onChange({ ...raw, courses: next, count: next.length })
  }

  return (
    <div className="space-y-4">
      {courses.map((c, i) => (
        <CheckboxRow
          key={i}
          checked={checkedSet.has(i)}
          onChange={(v) => onToggleCheck(i, v)}
          title={`#${i + 1} ${c.name || "（科目名なし）"}`}
          description={[c.code, c.term, c.room].filter(Boolean).join(" / ")}
        >
          <div className="space-y-3 relative">
            <div className="absolute right-0 -top-1">
              <RemoveButton onClick={() => removeCourse(i)} />
            </div>

            {/* Basic fields */}
            <div className="grid grid-cols-2 gap-2">
              <Field label="コード" value={c.code} onChange={(v) => updateCourse(i, { code: v })} />
              <Field label="科目名" value={c.name} onChange={(v) => updateCourse(i, { name: v })} />
              <Field
                label="学年"
                value={c.year_level ?? 1}
                onChange={(v) => updateCourse(i, { year_level: Number(v) || 1 })}
              />
              <Field
                label="クラス区分"
                value={c.class_section ?? ""}
                onChange={(v) => updateCourse(i, { class_section: v })}
              />
              <SelectField
                label="学期"
                value={c.term ?? "前期"}
                options={VALID_TERMS}
                onChange={(v) => updateCourse(i, { term: v })}
              />
              <Field
                label="教室"
                value={c.room ?? ""}
                onChange={(v) => updateCourse(i, { room: v })}
              />
              <div className="col-span-2">
                <Field
                  label="備考"
                  value={c.notes ?? ""}
                  onChange={(v) => updateCourse(i, { notes: v })}
                />
              </div>
            </div>

            {/* Instructors — individual fields */}
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">担当教員</p>
              {(c.instructors ?? [""]).map((instr, ii) => (
                <div key={ii} className="flex gap-1 items-center">
                  <input
                    className="flex-1 text-sm border rounded px-1.5 py-0.5 bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    value={instr}
                    onChange={(e) => {
                      const arr = [...(c.instructors ?? [""])]
                      arr[ii] = e.target.value
                      updateCourse(i, { instructors: arr })
                    }}
                  />
                  {(c.instructors ?? []).length > 1 && (
                    <RemoveButton onClick={() => {
                      updateCourse(i, { instructors: (c.instructors ?? []).filter((_, idx) => idx !== ii) })
                    }} />
                  )}
                </div>
              ))}
              <AddRowButton onClick={() => {
                updateCourse(i, { instructors: [...(c.instructors ?? []), ""] })
              }} label="+ 教員を追加" />
            </div>

            {/* Schedules (day + period only) */}
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">曜日・時限</p>
              {(c.schedules ?? []).map((s, si) => (
                <div key={si} className="flex gap-2 items-end">
                  <SelectField
                    label="曜日"
                    value={s.day}
                    options={VALID_DAYS}
                    onChange={(v) => {
                      const sc = [...(c.schedules ?? [])]
                      sc[si] = { ...sc[si], day: v }
                      updateCourse(i, { schedules: sc })
                    }}
                  />
                  <SelectField
                    label="時限"
                    value={s.period}
                    options={VALID_PERIODS}
                    onChange={(v) => {
                      const sc = [...(c.schedules ?? [])]
                      sc[si] = { ...sc[si], period: Number(v) || 1 }
                      updateCourse(i, { schedules: sc })
                    }}
                  />
                  <RemoveButton onClick={() => {
                    updateCourse(i, { schedules: (c.schedules ?? []).filter((_, idx) => idx !== si) })
                  }} />
                </div>
              ))}
              <AddRowButton onClick={() => {
                updateCourse(i, { schedules: [...(c.schedules ?? []), { day: "月", period: 1 }] })
              }} />
            </div>

            {/* Targets */}
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">対象</p>
              {(c.targets ?? []).map((t, ti) => (
                <div key={ti} className="grid grid-cols-3 gap-1.5 items-end">
                  <Field label="コード" value={t.target_code} onChange={(v) => {
                    const tgt = [...(c.targets ?? [])]
                    tgt[ti] = { ...tgt[ti], target_code: v }
                    updateCourse(i, { targets: tgt })
                  }} />
                  <Field label="名称" value={t.target_name} onChange={(v) => {
                    const tgt = [...(c.targets ?? [])]
                    tgt[ti] = { ...tgt[ti], target_name: v }
                    updateCourse(i, { targets: tgt })
                  }} />
                  <div className="flex gap-1 items-end">
                    <Field label="備考" value={t.note ?? ""} onChange={(v) => {
                      const tgt = [...(c.targets ?? [])]
                      tgt[ti] = { ...tgt[ti], note: v }
                      updateCourse(i, { targets: tgt })
                    }} />
                    <RemoveButton onClick={() => {
                      updateCourse(i, { targets: (c.targets ?? []).filter((_, idx) => idx !== ti) })
                    }} />
                  </div>
                </div>
              ))}
              <AddRowButton onClick={() => {
                updateCourse(i, { targets: [...(c.targets ?? []), { target_code: "", target_name: "", note: "" }] })
              }} />
            </div>
          </div>
        </CheckboxRow>
      ))}
      <AddRowButton onClick={addCourse} />
    </div>
  )
}

// =============================================================================
// Changelog editor
// =============================================================================

function ChangelogEditor({
  raw,
  onChange,
  checkedSet,
  onToggleCheck,
}: {
  raw: ChangelogRawJson
  onChange: (r: ChangelogRawJson) => void
  checkedSet: Set<number>
  onToggleCheck: (index: number, checked: boolean) => void
}) {
  const changes = raw.changes ?? []

  const updateChange = (i: number, patch: Partial<RawChange>) => {
    const next = [...changes]
    next[i] = { ...next[i], ...patch }
    onChange({ ...raw, changes: next, count: next.length })
  }

  const addChange = () => {
    onChange({
      ...raw,
      changes: [...changes, { change_type: "update", course_name: "", changes: [] }],
      count: changes.length + 1,
    })
  }

  const removeChange = (i: number) => {
    const next = changes.filter((_, idx) => idx !== i)
    onChange({ ...raw, changes: next, count: next.length })
  }

  return (
    <div className="space-y-3">
      {changes.map((c, i) => (
        <CheckboxRow
          key={i}
          checked={checkedSet.has(i)}
          onChange={(v) => onToggleCheck(i, v)}
          title={`#${i + 1} ${CHANGE_TYPE_LABEL[c.change_type] || "変更"} - ${c.course_name || "（科目名なし）"}`}
          description={[c.course_code, c.term, c.day, c.period ? `${c.period}限` : ""].filter(Boolean).join(" / ")}
        >
          <div className="space-y-2 relative">
            <div className="absolute right-0 -top-1">
              <RemoveButton onClick={() => removeChange(i)} />
            </div>

            <div className="pr-12 w-1/2 min-w-[120px]">
              <SelectField
                label="タイプ"
                value={c.change_type}
                options={CHANGE_TYPES}
                optionLabels={CHANGE_TYPE_LABEL}
                onChange={(v) => updateChange(i, { change_type: v as RawChange["change_type"] })}
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Field label="科目コード" value={c.course_code ?? ""} onChange={(v) => updateChange(i, { course_code: v || null })} />
              <Field label="科目名" value={c.course_name ?? ""} onChange={(v) => updateChange(i, { course_name: v })} />
              <SelectField
                label="学期"
                value={c.term ?? ""}
                options={["", ...VALID_TERMS]}
                onChange={(v) => updateChange(i, { term: v || null })}
              />
              <SelectField
                label="曜日"
                value={c.day ?? ""}
                options={["", ...VALID_DAYS]}
                onChange={(v) => updateChange(i, { day: v || null })}
              />
              <SelectField
                label="時限"
                value={c.period != null ? String(c.period) : ""}
                options={["", ...VALID_PERIODS.map(String)]}
                onChange={(v) => updateChange(i, { period: v ? (Number(v) || v) : null })}
              />
            </div>

            {/* Field changes (for update type) */}
            {c.change_type === "update" && (
              <div className="space-y-1">
                <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">変更フィールド</p>
                {(c.changes ?? []).map((fc, fi) => (
                  <div key={fi} className="grid grid-cols-3 gap-1.5 items-end">
                    <Field label="フィールド名" value={fc.field} onChange={(v) => {
                      const fcs = [...(c.changes ?? [])]
                      fcs[fi] = { ...fcs[fi], field: v }
                      updateChange(i, { changes: fcs })
                    }} />
                    <Field label="変更前" value={fc.old_value ?? ""} onChange={(v) => {
                      const fcs = [...(c.changes ?? [])]
                      fcs[fi] = { ...fcs[fi], old_value: v || null }
                      updateChange(i, { changes: fcs })
                    }} />
                    <div className="flex gap-1 items-end">
                      <Field label="変更後" value={fc.new_value ?? ""} onChange={(v) => {
                        const fcs = [...(c.changes ?? [])]
                        fcs[fi] = { ...fcs[fi], new_value: v || null }
                        updateChange(i, { changes: fcs })
                      }} />
                      <RemoveButton onClick={() => {
                        updateChange(i, { changes: (c.changes ?? []).filter((_, idx) => idx !== fi) })
                      }} />
                    </div>
                  </div>
                ))}
                <AddRowButton onClick={() => {
                  updateChange(i, { changes: [...(c.changes ?? []), { field: "", old_value: null, new_value: null }] })
                }} />
              </div>
            )}
          </div>
        </CheckboxRow>
      ))}
      <AddRowButton onClick={addChange} />
    </div>
  )
}

// =============================================================================
// Advance enrollment editor
// =============================================================================

function AdvanceEditor({
  raw,
  onChange,
  checkedSet,
  onToggleCheck,
}: {
  raw: AdvanceRawJson
  onChange: (r: AdvanceRawJson) => void
  checkedSet: Set<number>
  onToggleCheck: (index: number, checked: boolean) => void
}) {
  const names = raw.names ?? []

  const updateName = (i: number, v: string) => {
    const next = [...names]
    next[i] = v
    onChange({ ...raw, names: next, count: next.length })
  }

  const addName = () => {
    onChange({ ...raw, names: [...names, ""], count: names.length + 1 })
  }

  const removeName = (i: number) => {
    const next = names.filter((_, idx) => idx !== i)
    onChange({ ...raw, names: next, count: next.length })
  }

  return (
    <div className="space-y-1.5">
      {names.map((name, i) => (
        <SimpleCheckboxRow
          key={i}
          checked={checkedSet.has(i)}
          onChange={(v) => onToggleCheck(i, v)}
        >
          <div className="flex items-center gap-2">
            <input
              className="flex-1 text-sm border rounded px-2 py-1 bg-background focus:outline-none focus:ring-1 focus:ring-primary"
              value={name}
              placeholder="科目名を入力"
              onChange={(e) => updateName(i, e.target.value)}
            />
            <RemoveButton onClick={() => removeName(i)} />
          </div>
        </SimpleCheckboxRow>
      ))}
      <AddRowButton onClick={addName} />
    </div>
  )
}

// =============================================================================
// ReviewPage
// =============================================================================

function getItemCount(pdfType: string, raw: ExtractionRawJson): number {
  if (pdfType === "timetable") return ((raw as TimetableRawJson).courses ?? []).length
  if (pdfType === "changelog") return ((raw as ChangelogRawJson).changes ?? []).length
  if (pdfType === "advance_enrollment") return ((raw as AdvanceRawJson).names ?? []).length
  return 0
}

export function ReviewPage() {
  const { extractionId } = useParams<{ extractionId: string }>()
  const navigate = useNavigate()

  const [extraction, setExtraction] = useState<Extraction | null>(null)
  const [editedJson, setEditedJson] = useState<ExtractionRawJson | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [acting, setActing] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [checkedSet, setCheckedSet] = useState<Set<number>>(new Set())

  const pdfType = extraction?.pdf_type ?? "timetable"
  const itemCount = editedJson ? getItemCount(pdfType, editedJson) : 0
  const allChecked = itemCount > 0 && checkedSet.size === itemCount

  const toggleCheck = (index: number, checked: boolean) => {
    setCheckedSet((prev) => {
      const next = new Set(prev)
      if (checked) next.add(index)
      else next.delete(index)
      return next
    })
  }

  const toggleAll = () => {
    if (allChecked) {
      setCheckedSet(new Set())
    } else {
      setCheckedSet(new Set(Array.from({ length: itemCount }, (_, i) => i)))
    }
  }

  useEffect(() => {
    if (!extractionId) return
    const fetchData = async () => {
      setLoading(true)
      const { data, error: err } = await supabase
        .from("extractions")
        .select("*")
        .eq("id", extractionId)
        .single()
      if (err) {
        setError("抽出レコードの取得に失敗しました: " + err.message)
      } else {
        setExtraction(data as Extraction)
        setEditedJson((data.raw_json as unknown as ExtractionRawJson) ?? null)
      }
      setLoading(false)
    }
    fetchData()
  }, [extractionId])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const handleApprove = async () => {
    if (!extraction || !editedJson) return

    const status = extraction.status ?? "pending"
    if (status === "extracted" && !allChecked) return

    setActing(true)

    const result = await approveExtraction(extraction.id, pdfType, editedJson)

    if (!result.ok) {
      showToast("承認に失敗しました: " + result.error)
    } else {
      showToast(`${status === "approved" ? "再反映完了" : "承認完了"} — ${result.count} 件を反映しました`)
      setTimeout(() => navigate("/admin"), 1200)
    }
    setActing(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        読み込み中…
      </div>
    )
  }

  if (error || !extraction) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-destructive">{error ?? "データが見つかりません"}</p>
        <button onClick={() => navigate("/admin")} className="text-sm text-primary underline">
          戻る
        </button>
      </div>
    )
  }

  const status = extraction.status ?? "pending"
  const badge = STATUS_LABELS[status] ?? { label: status, color: "bg-muted text-muted-foreground" }
  const isReviewable = status === "extracted" || status === "approved"
  const requiresChecklist = status === "extracted"
  const canSubmit = !acting && (!requiresChecklist || allChecked)

  const title = `${PDF_TYPE_LABELS[pdfType] ?? pdfType}${
    extraction.semester === "spring" ? "（前期）" : extraction.semester === "fall" ? "（後期）" : ""
  }${extraction.academic_year ? ` ${extraction.academic_year}年度` : ""}`

  return (
    <div className="relative flex min-h-full flex-col lg:h-full lg:overflow-hidden">
      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-foreground text-background text-sm px-4 py-2 rounded-lg shadow-lg">
          {toast}
        </div>
      )}

      <PageHeader title={title}>
        <div className="flex w-full items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
              {badge.label}
            </span>
            <span className="hidden sm:inline-block truncate max-w-[150px] md:max-w-md" title={extraction.pdf_url}>
              {extraction.pdf_url.split("/").slice(-2).join("/")}
            </span>
          </div>

          {/* Approve button */}
          {isReviewable && (
            <div className="flex items-center gap-2 md:gap-3 shrink-0">
              {requiresChecklist && (
                <>
                  <button
                    type="button"
                    onClick={toggleAll}
                    className="text-xs text-muted-foreground hover:text-foreground hidden md:block"
                  >
                    {allChecked ? "全選択解除" : "全選択"}
                  </button>
                  <span className="text-xs text-muted-foreground hidden sm:block">
                    {checkedSet.size}/{itemCount}
                  </span>
                </>
              )}
              <button
                onClick={handleApprove}
                disabled={!canSubmit}
                className="h-8 md:h-9 px-3 md:px-4 rounded-md bg-primary text-primary-foreground text-xs md:text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                title={requiresChecklist && !allChecked ? "すべての項目にチェックを入れてください" : ""}
              >
                {acting ? "処理中…" : status === "approved" ? "再反映して更新" : "承認して反映"}
              </button>
            </div>
          )}
        </div>
      </PageHeader>

      <div className="flex min-h-0 flex-1 flex-col px-2 py-4 pt-14 md:px-6 md:pt-4">
        <div className="mb-4 shrink-0 px-2 md:px-0">
          <button
            onClick={() => navigate("/admin")}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            ← 一覧へ戻る
          </button>
        </div>

        {/* Main split layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-0">
          {/* Left: PDF viewer */}
        <div className="flex flex-col rounded-xl border overflow-hidden">
          <div className="px-4 py-2 bg-muted/40 text-xs font-medium text-muted-foreground border-b shrink-0">
            PDF ビュー
          </div>
          <iframe
            src={extraction.pdf_url + "#toolbar=0"}
            className="w-full flex-1"
            title="PDF preview"
          />
        </div>

        {/* Right: Editable extracted data */}
        <div className="flex flex-col rounded-xl border overflow-hidden">
          <div className="px-4 py-2 bg-muted/40 text-xs font-medium text-muted-foreground border-b shrink-0 flex items-center gap-2">
            <span>抽出データ（編集可）</span>
            <span className="ml-auto text-xs">{itemCount} 件</span>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {editedJson === null ? (
              <p className="text-sm text-muted-foreground">JSON データなし</p>
            ) : pdfType === "timetable" ? (
              <TimetableEditor
                raw={editedJson as TimetableRawJson}
                onChange={setEditedJson}
                checkedSet={checkedSet}
                onToggleCheck={toggleCheck}
              />
            ) : pdfType === "changelog" ? (
              <ChangelogEditor
                raw={editedJson as ChangelogRawJson}
                onChange={setEditedJson}
                checkedSet={checkedSet}
                onToggleCheck={toggleCheck}
              />
            ) : pdfType === "advance_enrollment" ? (
              <AdvanceEditor
                raw={editedJson as AdvanceRawJson}
                onChange={setEditedJson}
                checkedSet={checkedSet}
                onToggleCheck={toggleCheck}
              />
            ) : (
              <pre className="text-xs bg-muted rounded-lg p-4 overflow-auto">
                {JSON.stringify(editedJson, null, 2)}
              </pre>
            )}
          </div>
        </div>
        </div>

        {/* Already processed */}
        {!isReviewable && (
          <div className="pt-4 text-sm text-muted-foreground shrink-0 px-2 md:px-0 pb-6 lg:pb-0">
            このタスクはすでに処理済みです（{badge.label}）。
          </div>
        )}
      </div>
    </div>
  )
}
