import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { supabase } from "@/lib/supabase"
import type { Extraction } from "@/lib/database.types"
import { ExtractionTableSkeleton } from "@/components/admin/AdminSkeleton"
import { StatusBadge } from "@/components/admin/StatusBadge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Card } from "@/components/ui/card"
import { IconFileText, IconChevronRight } from "@tabler/icons-react"

type StatusFilter = "all" | "extracted" | "approved" | "pending"

const PDF_TYPE_LABELS: Record<string, string> = {
  timetable: "授業時間表",
  changelog: "変更一覧",
  advance_enrollment: "先行履修",
}

const SEMESTER_LABELS: Record<string, string> = {
  spring: "前期",
  fall: "後期",
}

function formatDate(iso: string | null): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function ExtractionList() {
  const navigate = useNavigate()
  const [extractions, setExtractions] = useState<Extraction[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<StatusFilter>("extracted")
  const [latestYearOnly, setLatestYearOnly] = useState(true)
  const [latestOnly, setLatestOnly] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      const { data, error: err } = await supabase
        .from("extractions")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(100)

      if (err) {
        setError("データの取得に失敗しました: " + err.message)
      } else {
        setExtractions((data as Extraction[]) ?? [])
      }
      setLoading(false)
    }

    fetchData()
  }, [])

  // Identify latest academic year present across ALL extractions regardless of current tab
  const maxYear = useMemo(() => {
    return extractions.reduce((max, ext) => {
      if (ext.academic_year && ext.academic_year > max) return ext.academic_year
      return max
    }, 0)
  }, [extractions])

  // Filter by status tab
  const statusFilteredExtractions = useMemo(() => {
    if (filter === "all") return extractions
    return extractions.filter((ext) => (ext.status ?? "pending") === filter)
  }, [extractions, filter])

  // Filter by latest year and/or latest of each document identity
  const displayedExtractions = useMemo(() => {
    let list = statusFilteredExtractions

    if (latestYearOnly && maxYear > 0) {
      list = list.filter((ext) => ext.academic_year === maxYear)
    }

    if (!latestOnly) return list

    const seen = new Set<string>()
    return list.filter((ext) => {
      // Group by document identity: (academic_year, pdf_type, semester)
      const docKey = `${ext.academic_year ?? "any"}_${ext.pdf_type ?? "unknown"}_${ext.semester ?? "all"}`
      if (seen.has(docKey)) return false
      seen.add(docKey)
      return true
    })
  }, [statusFilteredExtractions, latestYearOnly, maxYear, latestOnly])

  return (
    <div className="space-y-4">
      {/* Filter tabs and Latest Only / Latest Year Toggle */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs
          value={filter}
          onValueChange={(v) => setFilter(v as StatusFilter)}
          className="w-auto"
        >
          <TabsList>
            <TabsTrigger value="extracted">承認待ち</TabsTrigger>
            <TabsTrigger value="all">すべて</TabsTrigger>
            <TabsTrigger value="approved">承認済み</TabsTrigger>
            <TabsTrigger value="pending">処理中</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex flex-wrap items-center gap-2">
          {/* Latest Year Only Toggle */}
          <Button
            type="button"
            variant={latestYearOnly ? "secondary" : "outline"}
            size="sm"
            onClick={() => setLatestYearOnly((prev) => !prev)}
            className="w-fit gap-2 text-xs font-medium"
          >
            <Checkbox
              checked={latestYearOnly}
              className="pointer-events-none size-3.5"
            />
            <span>最新年度のみ{maxYear ? ` (${maxYear}年度)` : ""}</span>
          </Button>

          {/* Latest Only Toggle */}
          <Button
            type="button"
            variant={latestOnly ? "secondary" : "outline"}
            size="sm"
            onClick={() => setLatestOnly((prev) => !prev)}
            className="w-fit gap-2 text-xs font-medium"
          >
            <Checkbox
              checked={latestOnly}
              className="pointer-events-none size-3.5"
            />
            <span>最新版のみ</span>
            <span className="text-[11px] text-muted-foreground">
              ({displayedExtractions.length} / {statusFilteredExtractions.length}件)
            </span>
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {loading && <ExtractionTableSkeleton />}

      {/* Error state */}
      {error && !loading && (
        <Card className="py-12 text-center text-destructive shadow-xs">
          {error}
        </Card>
      )}

      {/* Empty state */}
      {!loading && !error && displayedExtractions.length === 0 && (
        <Card className="py-12 text-center text-muted-foreground shadow-xs">
          該当する抽出タスクがありません
        </Card>
      )}

      {/* Table */}
      {!loading && !error && displayedExtractions.length > 0 && (
        <Card className="gap-0 overflow-hidden rounded-xl border py-0 shadow-xs">
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow>
                <TableHead className="font-semibold text-muted-foreground">
                  種別
                </TableHead>
                <TableHead className="font-semibold text-muted-foreground">
                  学期
                </TableHead>
                <TableHead className="font-semibold text-muted-foreground">
                  年度
                </TableHead>
                <TableHead className="font-semibold text-muted-foreground">
                  ステータス
                </TableHead>
                <TableHead className="font-semibold text-muted-foreground">
                  更新日時
                </TableHead>
                <TableHead className="text-right font-semibold text-muted-foreground">
                  操作
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayedExtractions.map((ext) => {
                const status = ext.status ?? "pending"

                return (
                  <TableRow
                    key={ext.id}
                    className="cursor-pointer transition-colors hover:bg-muted/40"
                    onClick={() => navigate(`/admin/review/${ext.id}`)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <IconFileText className="size-4 shrink-0 text-muted-foreground" />
                        <span className="font-medium">
                          {PDF_TYPE_LABELS[ext.pdf_type ?? ""] ??
                            ext.pdf_type ??
                            "—"}
                        </span>
                        {latestOnly && (
                          <Badge
                            variant="secondary"
                            className="h-4 px-1.5 py-0 text-[10px] font-normal"
                          >
                            最新
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">
                        {SEMESTER_LABELS[ext.semester ?? ""] ??
                          ext.semester ??
                          "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {ext.academic_year ? `${ext.academic_year}年度` : "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={ext.status} />
                    </TableCell>
                    <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
                      {formatDate(ext.updated_at ?? ext.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="gap-1 text-primary hover:bg-primary/5 hover:text-primary"
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/admin/review/${ext.id}`)
                        }}
                      >
                        <span>
                          {status === "extracted" ? "レビュー" : "詳細"}
                        </span>
                        <IconChevronRight className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}
