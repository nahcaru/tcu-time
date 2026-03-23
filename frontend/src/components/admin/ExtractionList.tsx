import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import { supabase } from "@/lib/supabase"
import type { Extraction } from "@/lib/database.types"

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

  const filters: { value: StatusFilter; label: string }[] = [
    { value: "all",       label: "すべて" },
    { value: "extracted", label: "承認待ち" },
    { value: "approved",  label: "承認済み" },
    { value: "pending",   label: "処理中" },
  ]

  return (
    <div className="space-y-4">
      {/* Filter tabs */}
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

      {/* Loading / error states */}
      {loading && (
        <div className="text-center py-12 text-muted-foreground">読み込み中…</div>
      )}
      {error && (
        <div className="text-center py-12 text-destructive">{error}</div>
      )}
      {!loading && !error && extractions.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          該当する抽出タスクがありません
        </div>
      )}

      {/* Table */}
      {!loading && !error && extractions.length > 0 && (
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
              {extractions.map((ext) => {
                const status = ext.status ?? "pending"
                const badge = STATUS_LABELS[status] ?? { label: status, color: "bg-muted text-muted-foreground" }
                return (
                  <tr
                    key={ext.id}
                    className="hover:bg-muted/30 transition-colors cursor-pointer"
                    onClick={() => navigate(`/admin/review/${ext.id}`)}
                  >
                    <td className="px-4 py-3">
                      {PDF_TYPE_LABELS[ext.pdf_type ?? ""] ?? ext.pdf_type ?? "—"}
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
