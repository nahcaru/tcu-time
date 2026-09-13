import { useCallback, useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router"
import { supabase } from "@/lib/supabase"
import type { Extraction } from "@/lib/database.types"
import {
  approveExtraction,
  saveReviewDraft,
  getSavedReviewIndices,
  inferTerm,
  type TimetableRawJson,
  type ChangelogRawJson,
  type AdvanceRawJson,
  type ExtractionRawJson,
} from "@/lib/approvalService"
import { PageHeader } from "@/components/layout/PageHeader"
import { ReviewPageSkeleton } from "@/components/admin/AdminSkeleton"
import { StatusBadge } from "@/components/admin/StatusBadge"
import { TimetableEditor } from "@/components/admin/review/TimetableEditor"
import { ChangelogEditor } from "@/components/admin/review/ChangelogEditor"
import { AdvanceEditor } from "@/components/admin/review/AdvanceEditor"
import { KeyboardShortcutsDialog } from "@/components/admin/review/KeyboardShortcutsDialog"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Kbd } from "@/components/ui/kbd"
import {
  IconArrowLeft,
  IconExternalLink,
  IconFileText,
  IconCheck,
  IconAlertCircle,
  IconKeyboard,
  IconDeviceFloppy,
} from "@tabler/icons-react"

const PDF_TYPE_LABELS: Record<string, string> = {
  timetable: "授業時間表",
  changelog: "変更一覧",
  advance_enrollment: "先行履修",
}

function getItemCount(pdfType: string, raw: ExtractionRawJson): number {
  if (pdfType === "timetable")
    return ((raw as TimetableRawJson).courses ?? []).length
  if (pdfType === "changelog")
    return ((raw as ChangelogRawJson).changes ?? []).length
  if (pdfType === "advance_enrollment")
    return ((raw as AdvanceRawJson).names ?? []).length
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
  const [savingDraft, setSavingDraft] = useState(false)
  const [toast, setToast] = useState<{
    message: string
    type: "success" | "error"
  } | null>(null)
  const [checkedSet, setCheckedSet] = useState<Set<number>>(new Set())
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set())
  const [activeIndex, setActiveIndex] = useState<number | null>(0)
  const [showShortcuts, setShowShortcuts] = useState(false)

  const pdfType = extraction?.pdf_type ?? "timetable"
  const itemCount = editedJson ? getItemCount(pdfType, editedJson) : 0
  const allChecked = itemCount > 0 && checkedSet.size === itemCount
  const status = extraction?.status ?? "pending"
  const isReviewable = status === "extracted" || status === "approved"
  const requiresChecklist = status === "extracted"
  const canSubmit = !acting && (!requiresChecklist || allChecked)

  const toggleCheck = (index: number, checked: boolean) => {
    setCheckedSet((prev) => {
      const next = new Set(prev)
      if (checked) next.add(index)
      else next.delete(index)
      return next
    })
    setExpandedSet((prev) => {
      const next = new Set(prev)
      if (checked) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const toggleExpand = (index: number) => {
    setExpandedSet((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const toggleAll = useCallback(() => {
    if (allChecked) {
      setCheckedSet(new Set())
      setExpandedSet(new Set(Array.from({ length: itemCount }, (_, i) => i)))
    } else {
      setCheckedSet(new Set(Array.from({ length: itemCount }, (_, i) => i)))
      setExpandedSet(new Set())
    }
  }, [allChecked, itemCount])

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
        const ext = data as Extraction
        setExtraction(ext)
        const rawJson = (ext.raw_json as unknown as ExtractionRawJson) ?? null
        setEditedJson(rawJson)
        if (rawJson) {
          const count = getItemCount(ext.pdf_type ?? "timetable", rawJson)
          const savedIndices = getSavedReviewIndices(rawJson)
          if (savedIndices) {
            const restoredSet = new Set(
              savedIndices.filter(
                (idx) => typeof idx === "number" && idx >= 0 && idx < count
              )
            )
            setCheckedSet(restoredSet)
            setExpandedSet(
              new Set(
                Array.from({ length: count }, (_, i) => i).filter(
                  (i) => !restoredSet.has(i)
                )
              )
            )
          } else {
            setCheckedSet(new Set())
            setExpandedSet(new Set(Array.from({ length: count }, (_, i) => i)))
          }
          setActiveIndex(0)
        }
      }
      setLoading(false)
    }
    fetchData()
  }, [extractionId])

  const showToast = (
    message: string,
    type: "success" | "error" = "success"
  ) => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  const handleApprove = useCallback(async () => {
    if (!extraction || !editedJson) return

    const status = extraction.status ?? "pending"
    if (status === "extracted" && !allChecked) return

    setActing(true)

    let finalJson = editedJson
    if (pdfType === "timetable") {
      const timetableData = editedJson as TimetableRawJson
      const normalizedCourses = (timetableData.courses ?? []).map((c) => ({
        ...c,
        term: inferTerm(c, extraction.semester || timetableData.semester),
      }))
      finalJson = {
        ...timetableData,
        courses: normalizedCourses,
      }
    }

    const result = await approveExtraction(extraction.id, pdfType, finalJson)

    if (!result.ok) {
      showToast("承認に失敗しました: " + result.error, "error")
    } else {
      showToast(
        `${status === "approved" ? "再反映完了" : "承認完了"} — ${result.count} 件を反映しました`,
        "success"
      )
      setTimeout(() => navigate("/admin"), 1200)
    }
    setActing(false)
  }, [extraction, editedJson, allChecked, pdfType, navigate])

  const handleSaveDraft = useCallback(async () => {
    if (!extraction || !editedJson || savingDraft || acting) return

    setSavingDraft(true)
    const checkedIndices = Array.from(checkedSet).sort((a, b) => a - b)
    const result = await saveReviewDraft(
      extraction.id,
      editedJson,
      checkedIndices
    )

    if (!result.ok) {
      showToast(
        "下書き保存に失敗しました: " + (result.error ?? "不明なエラー"),
        "error"
      )
    } else {
      setEditedJson((prev) =>
        prev
          ? {
              ...prev,
              _review_state: {
                checked_indices: checkedIndices,
                saved_at: new Date().toISOString(),
              },
            }
          : prev
      )
      showToast("下書きを保存しました", "success")
    }
    setSavingDraft(false)
  }, [extraction, editedJson, savingDraft, acting, checkedSet])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Allow Cmd+S or Ctrl+S to save draft even when focused in an input
      if ((e.metaKey || e.ctrlKey) && (e.key === "s" || e.key === "S")) {
        e.preventDefault()
        if (isReviewable && !savingDraft && !acting && editedJson) {
          handleSaveDraft()
        }
        return
      }

      // Allow Cmd+Enter or Ctrl+Enter even when focused in an input
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault()
        if (canSubmit && !savingDraft) {
          handleApprove()
        }
        return
      }

      // Ignore single-key shortcuts when user is typing in an input / textarea / select
      const target = e.target as HTMLElement | null
      const isInput =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)

      if (isInput) return

      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault()
        setActiveIndex((prev) => {
          if (itemCount === 0) return 0
          return Math.min(itemCount - 1, (prev ?? -1) + 1)
        })
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault()
        setActiveIndex((prev) => {
          if (itemCount === 0) return 0
          return Math.max(0, (prev ?? 1) - 1)
        })
      } else if (e.key === " " || e.key === "x") {
        e.preventDefault()
        if (activeIndex != null && activeIndex >= 0 && activeIndex < itemCount) {
          const willCheck = !checkedSet.has(activeIndex)
          toggleCheck(activeIndex, willCheck)
          if (willCheck && activeIndex < itemCount - 1) {
            setActiveIndex((prev) => (prev != null ? prev + 1 : 0))
          }
        }
      } else if (e.key === "Enter" || e.key === "o") {
        e.preventDefault()
        if (activeIndex != null && activeIndex >= 0 && activeIndex < itemCount) {
          toggleExpand(activeIndex)
        }
      } else if (e.key === "a" || e.key === "A") {
        e.preventDefault()
        toggleAll()
      } else if (e.key === "Escape") {
        e.preventDefault()
        if (showShortcuts) {
          setShowShortcuts(false)
        } else {
          navigate("/admin")
        }
      } else if (e.key === "?") {
        e.preventDefault()
        setShowShortcuts((prev) => !prev)
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [
    itemCount,
    activeIndex,
    checkedSet,
    canSubmit,
    handleApprove,
    handleSaveDraft,
    savingDraft,
    acting,
    isReviewable,
    editedJson,
    navigate,
    showShortcuts,
    allChecked,
    toggleAll,
  ])

  if (loading) {
    return (
      <div className="relative flex min-h-full flex-col pb-6 lg:h-full lg:overflow-hidden">
        <PageHeader title="抽出レビュー" />
        <div className="flex min-h-full w-full flex-1 flex-col px-4 py-4 pt-14 md:px-6 md:pt-4">
          <ReviewPageSkeleton />
        </div>
      </div>
    )
  }

  if (error || !extraction) {
    return (
      <div className="relative flex min-h-full flex-col pb-6">
        <PageHeader title="抽出レビュー" />
        <div className="flex min-h-full w-full flex-1 flex-col items-center justify-center px-4 py-12 pt-14 md:px-6 md:pt-4">
          <Card className="w-full max-w-md space-y-4 p-6 text-center shadow-xs">
            <div className="font-medium text-destructive">
              {error ?? "データが見つかりません"}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/admin")}
              className="gap-1.5"
            >
              <IconArrowLeft className="size-4" />
              一覧へ戻る
            </Button>
          </Card>
        </div>
      </div>
    )
  }

  const pdfFileName = extraction.pdf_url.split("/").slice(-2).join("/")

  const title = `${PDF_TYPE_LABELS[pdfType] ?? pdfType}${
    extraction.semester === "spring"
      ? "（前期）"
      : extraction.semester === "fall"
        ? "（後期）"
        : ""
  }${extraction.academic_year ? ` ${extraction.academic_year}年度` : ""}`

  return (
    <div className="relative flex min-h-full flex-col lg:h-full lg:overflow-hidden">
      {/* Feedback Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 animate-in duration-200 fade-in slide-in-from-bottom-3">
          <Card className="flex flex-row items-center gap-2 border-primary/20 bg-card px-4 py-2.5 text-sm font-medium text-card-foreground shadow-lg">
            {toast.type === "success" ? (
              <IconCheck className="size-4 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <IconAlertCircle className="size-4 text-destructive" />
            )}
            <span>{toast.message}</span>
          </Card>
        </div>
      )}

      <PageHeader title={title}>
        <div className="flex w-full items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
            <StatusBadge status={status} />
            <span
              className="hidden max-w-[150px] truncate font-mono text-xs sm:inline-block md:max-w-xs"
              title={extraction.pdf_url}
            >
              {pdfFileName}
            </span>
          </div>

          {/* Action buttons in header */}
          <div className="flex shrink-0 items-center gap-2">
            {isReviewable && requiresChecklist && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={toggleAll}
                  className="hidden text-xs text-muted-foreground hover:text-foreground md:inline-flex"
                >
                  {allChecked ? "全選択解除" : "全選択"}
                </Button>
                <Badge
                  variant="outline"
                  className="hidden text-xs sm:inline-flex"
                >
                  {checkedSet.size} / {itemCount} 確認済み
                </Badge>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowShortcuts(true)}
                  className="hidden gap-1 text-xs text-muted-foreground hover:text-foreground sm:inline-flex"
                  title="キーボードショートカット一覧を表示 (?)"
                >
                  <IconKeyboard className="size-3.5" />
                  <Kbd className="h-4 min-w-4 px-1 text-[10px]">?</Kbd>
                </Button>
              </>
            )}

            {/* 戻る button: positioned to the left of 承認 */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/admin")}
              className="gap-1 text-xs sm:text-sm"
            >
              <IconArrowLeft className="size-4" />
              <span>戻る</span>
            </Button>

            {/* 下書き保存 button */}
            {isReviewable && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleSaveDraft}
                disabled={savingDraft || acting || !editedJson}
                className="gap-1 text-xs sm:text-sm"
                title="編集内容と確認状態を下書きとして保存 (⌘S)"
              >
                <IconDeviceFloppy className="size-4" />
                <span>{savingDraft ? "保存中…" : "下書き保存"}</span>
              </Button>
            )}

            {/* 承認 button */}
            {isReviewable && (
              <Button
                onClick={handleApprove}
                disabled={!canSubmit || savingDraft}
                size="sm"
                className="text-xs sm:text-sm"
                title={
                  requiresChecklist && !allChecked
                    ? "すべての項目にチェックを入れてください"
                    : ""
                }
              >
                {acting ? "処理中…" : "承認"}
              </Button>
            )}
          </div>
        </div>
      </PageHeader>

      <div className="flex min-h-0 flex-1 flex-col px-4 py-4 pt-14 md:px-6 md:pt-4">
        {/* Main 2-column split layout */}
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Left: PDF viewer Card */}
          <Card className="flex h-full flex-col gap-0 overflow-hidden rounded-xl border py-0 shadow-xs">
            <div className="flex shrink-0 items-center justify-between border-b bg-muted/40 px-4 py-2.5">
              <div className="flex items-center gap-2">
                <IconFileText className="size-4 text-muted-foreground" />
                <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                  PDF プレビュー
                </span>
              </div>
              <a
                href={extraction.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                <span>別タブで開く</span>
                <IconExternalLink className="size-3.5" />
              </a>
            </div>
            <div className="min-h-[400px] flex-1 bg-muted/10 lg:min-h-0">
              <iframe
                src={extraction.pdf_url + "#toolbar=0"}
                className="h-full w-full border-0"
                title="PDF preview"
              />
            </div>
          </Card>

          {/* Right: Editable extracted data Card */}
          <Card className="flex h-full flex-col gap-0 overflow-hidden rounded-xl border py-0 shadow-xs">
            <div className="flex shrink-0 items-center justify-between border-b bg-muted/40 px-4 py-2.5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                  抽出データ（編集可）
                </span>
                <Badge
                  variant="secondary"
                  className="h-5 px-1.5 text-[11px] font-normal"
                >
                  {itemCount} 件
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                {requiresChecklist && (
                  <>
                    <span className="text-xs text-muted-foreground sm:hidden">
                      {checkedSet.size} / {itemCount}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="xs"
                      onClick={toggleAll}
                      className="text-xs text-primary md:hidden"
                    >
                      {allChecked ? "解除" : "全選択"}
                    </Button>
                  </>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="xs"
                  onClick={() => setShowShortcuts(true)}
                  className="gap-1 text-xs text-muted-foreground hover:text-foreground sm:hidden"
                  title="ショートカット (?)"
                >
                  <IconKeyboard className="size-3.5" />
                  <Kbd className="h-4 min-w-4 px-1 text-[10px]">?</Kbd>
                </Button>
              </div>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {editedJson === null ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  JSON データなし
                </p>
              ) : pdfType === "timetable" ? (
                <TimetableEditor
                  raw={editedJson as TimetableRawJson}
                  onChange={setEditedJson}
                  checkedSet={checkedSet}
                  onToggleCheck={toggleCheck}
                  extractionSemester={extraction.semester}
                  activeIndex={activeIndex}
                  onSelectIndex={setActiveIndex}
                  expandedSet={expandedSet}
                  onToggleExpand={toggleExpand}
                />
              ) : pdfType === "changelog" ? (
                <ChangelogEditor
                  raw={editedJson as ChangelogRawJson}
                  onChange={setEditedJson}
                  checkedSet={checkedSet}
                  onToggleCheck={toggleCheck}
                  activeIndex={activeIndex}
                  onSelectIndex={setActiveIndex}
                  expandedSet={expandedSet}
                  onToggleExpand={toggleExpand}
                />
              ) : pdfType === "advance_enrollment" ? (
                <AdvanceEditor
                  raw={editedJson as AdvanceRawJson}
                  onChange={setEditedJson}
                  checkedSet={checkedSet}
                  onToggleCheck={toggleCheck}
                  activeIndex={activeIndex}
                  onSelectIndex={setActiveIndex}
                />
              ) : (
                <pre className="overflow-auto rounded-lg bg-muted/50 p-4 font-mono text-xs">
                  {JSON.stringify(editedJson, null, 2)}
                </pre>
              )}
            </div>
          </Card>
        </div>

        {/* Keyboard shortcuts helper dialog */}
        <KeyboardShortcutsDialog
          open={showShortcuts}
          onOpenChange={setShowShortcuts}
        />

        {/* Already processed info */}
        {!isReviewable && (
          <div className="shrink-0 pt-3 text-sm text-muted-foreground">
            このタスクはすでに処理済みです（{status}）。
          </div>
        )}
      </div>
    </div>
  )
}
