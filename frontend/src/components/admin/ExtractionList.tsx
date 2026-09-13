import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { supabase } from "@/lib/supabase"
import type { Extraction } from "@/lib/database.types"
import { ExtractionTableSkeleton } from "@/components/admin/AdminSkeleton"

type StatusFilter = "all" | "extracted" | "approved" | "pending"

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending:   { label: "処理中",   color: "bg-yellow-100 text-yellow-800" },
  extracted: { label: "承認待ち", color: "bg-blue-100 text-blue-800" },
  approved:  { label: "承認済み", color: "bg-green-100 text-green-800" },
}

const PDF_TYPE_LABELS: Record<string, string> = {
  timetable:          "時間割",
  changelog:          "変更一覧",
  advance_enrollment: "先行履修",
}

const SEMESTER_LABELS: Record<string, string> = {
  spring: "前期",
  fall:   "後期",
}

function formatDate(iso: string | null): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleString("ja-JP", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  })
}

export function ExtractionList() {
  const navigate = useNavigate()
  const [extractions, setExtractions] = useState<Extraction[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<StatusFilter>("extracted")
  const [latestOnly, setLatestOnly] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      const query = supabase
        .from("extractions")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(100)

      if (filter !== "all") {
        query.eq("status", filter)
      }

      const { data, error: err } = await query
      if (err) {
        setError("データの取得に失敗しました: " + err.message)
      } else {
        setExtractions((data as Extraction[]) ?? [])
      }
      setLoading(false)
    }

    fetchData()
  }, [filter])

  // Solely list the latest of each document type when latestOnly is true
  const displayedExtractions = useMemo(() => {
    if (!latestOnly) return extractions

    const seen = new Set<string>()
    return extractions.filter((ext) => {
      // Group by document identity: (pdf_type, semester)
      const docKey = `${ext.pdf_type ?? "unknown"}_${ext.semester ?? "all"}`
      if (seen.has(docKey)) return false
      seen.add(docKey)
      return true
    })
  }, [extractions, latestOnly])

  const filters: { value: StatusFilter; label: string }[] = [
    { value: "all",       label: "すべて" },
    { value: "extracted", label: "承認待ち" },
    { value: "approved",  label: "承認済み" },
    { value: "pending",   label: "処理中" },
  ]

  return (
    <div className="space-y-4">
      {/* Filter tabs and Latest Only Toggle */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-2 flex-wrap">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/70"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Latest Only Toggle */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setLatestOnly((prev) => !prev)}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              latestOnly
                ? "bg-secondary text-secondary-foreground border-border shadow-xs"
                : "bg-background text-muted-foreground border-border/80 hover:bg-muted/50"
            }`}
          >
            <span className={latestOnly ? "text-primary" : "text-muted-foreground"}>
              {latestOnly ? "✓" : "○"}
            </span>
            <span>各書類の最新版のみ表示</span>
            <span className="text-[10px] text-muted-foreground ml-0.5">
              ({displayedExtractions.length} / {extractions.length}件)
            </span>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {loading && <ExtractionTableSkeleton />}

      {/* Error state */}
      {error && !loading && (
        <div className="text-center py-12 text-destructive">{error}</div>
      )}

      {/* Empty state */}
      {!loading && !error && displayedExtractions.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          該当する抽出タスクがありません
        </div>
      )}

      {/* Table */}
      {!loading && !error && displayedExtractions.length > 0 && (
        <div className="rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">種別</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">学期</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">年度</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">PDF URL</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">ステータス</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">更新日時</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {displayedExtractions.map((ext) => {
                const status = ext.status ?? "pending"
                const badge = STATUS_LABELS[status] ?? { label: status, color: "bg-muted text-muted-foreground" }
                return (
                  <tr
                    key={ext.id}
                    className="hover:bg-muted/30 transition-colors cursor-pointer"
                    onClick={() => navigate(`/admin/review/${ext.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span>{PDF_TYPE_LABELS[ext.pdf_type ?? ""] ?? ext.pdf_type ?? "—"}</span>
                        {latestOnly && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-muted text-muted-foreground font-mono">
                            最新
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {SEMESTER_LABELS[ext.semester ?? ""] ?? ext.semester ?? "—"}
                    </td>
                    <td className="px-4 py-3">{ext.academic_year ?? "—"}</td>
                    <td className="px-4 py-3 max-w-xs truncate" title={ext.pdf_url}>
                      {ext.pdf_url.split("/").slice(-2).join("/")}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {formatDate(ext.updated_at ?? ext.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      {status === "extracted" && (
                        <span className="text-primary text-xs font-medium">
                          レビュー →
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
