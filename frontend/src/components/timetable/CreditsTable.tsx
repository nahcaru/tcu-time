import { useState, useMemo, useEffect } from "react"
import { useSettings } from "@/hooks/use-settings"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TARGETS } from "@/lib/constants"
import type { CourseWithRelations } from "@/lib/database.types"

interface CreditsTableProps {
  termType: "前期" | "後期"
  enrolledCourses: CourseWithRelations[]
}

export function CreditsTable({ termType, enrolledCourses }: CreditsTableProps) {
  const isSpring = termType === "前期"
  const { settings, updateSettings } = useSettings()

  const selectedTarget = settings?.department || "02"
  const isNuclear = selectedTarget === "06"

  const setSelectedTarget = (value: string) => {
    updateSettings({ department: value })
  }

  const earnedCredits = useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const credits = settings?.earned_credits as any
    const parse = (v: any) =>
      typeof v === "number" ? v : typeof v === "string" ? parseFloat(v) || 0 : 0

    return {
      practical: parse(credits?.practical),
      research: parse(credits?.research),
      lectures: parse(credits?.lectures),
    }
  }, [settings?.earned_credits])

  // Editable earned credits
  const [earnedPractical, setEarnedPractical] = useState(0)
  const [earnedResearch, setEarnedResearch] = useState(0)
  const [earnedLectures, setEarnedLectures] = useState(0)

  // Sync from settings to local state
  useEffect(() => {
    setEarnedPractical(earnedCredits.practical)
    setEarnedResearch(earnedCredits.research)
    setEarnedLectures(earnedCredits.lectures)
  }, [earnedCredits])

  // Debounce updates to settings
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      const current = {
        practical: earnedPractical,
        research: earnedResearch,
        lectures: earnedLectures,
      }
      if (JSON.stringify(current) !== JSON.stringify(earnedCredits)) {
        updateSettings({ earned_credits: current })
      }
    }, 1000)

    return () => clearTimeout(timeoutId)
  }, [
    earnedPractical,
    earnedResearch,
    earnedLectures,
    updateSettings,
    earnedCredits,
  ])

  // Requirements
  const reqPractical = isNuclear ? 2 : 4
  const reqResearch = 8
  const reqSubtotal = isNuclear ? 10 : 12
  const reqLectures = isNuclear ? 20 : 18
  const reqTotal = 30

  // Compute term credits safely for all categories
  const computedCredits = useMemo(() => {
    const spring = { practical: 0, research: 0, lectures: 0 }
    const fall = { practical: 0, research: 0, lectures: 0 }

    for (const course of enrolledCourses) {
      const credits = course.course_metadata[0]?.credits ?? 0
      const category = course.course_metadata[0]?.category

      const hasSpring = course.schedules.some((s) => s.term.startsWith("前"))
      const hasFall = course.schedules.some((s) => s.term.startsWith("後"))

      // Define bucket based on category
      let bucket: "practical" | "research" | "lectures" = "lectures"
      if (category === "実習・演習") bucket = "practical"
      else if (category === "特別研究") bucket = "research"

      if (hasSpring) spring[bucket] += credits
      if (hasFall) fall[bucket] += credits
    }
    return { spring, fall }
  }, [enrolledCourses])

  // Current term credits to display on column 3
  const currentTermCredits = isSpring
    ? computedCredits.spring
    : computedCredits.fall

  // First column base values (with Spring addition if checking Fall view)
  const basePractical =
    earnedPractical + (isSpring ? 0 : computedCredits.spring.practical)
  const baseResearch =
    earnedResearch + (isSpring ? 0 : computedCredits.spring.research)
  const baseLectures =
    earnedLectures + (isSpring ? 0 : computedCredits.spring.lectures)

  // Totals for Column 4 (Grand total in that row)
  const totalPractical = basePractical + currentTermCredits.practical
  const totalResearch = baseResearch + currentTermCredits.research
  const totalLectures = baseLectures + currentTermCredits.lectures

  const totalSubtotal = totalPractical + totalResearch
  const grandTotal = totalSubtotal + totalLectures

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-semibold text-muted-foreground">
          単位修得状況
        </h3>
        <Select value={selectedTarget} onValueChange={setSelectedTarget}>
          <SelectTrigger className="h-8 bg-background text-sm">
            <SelectValue placeholder="専攻を選択" />
          </SelectTrigger>
          <SelectContent>
            {TARGETS.map((t) => (
              <SelectItem key={t.code} value={t.code}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col overflow-hidden rounded-md border bg-card">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-1/5 whitespace-nowrap">項目</TableHead>
                <TableHead className="w-1/5 text-right whitespace-nowrap">
                  {isSpring ? "修得済" : "修得済+前期"}
                </TableHead>
                <TableHead className="w-1/5 text-right whitespace-nowrap">
                  {termType}
                </TableHead>
                <TableHead className="w-1/5 bg-muted/10 text-right font-bold whitespace-nowrap text-foreground">
                  合計
                </TableHead>
                <TableHead className="w-1/5 text-right whitespace-nowrap text-muted-foreground">
                  修了要件
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* 実習・演習 */}
              <TableRow>
                <TableCell className="font-medium text-muted-foreground">
                  実習・演習
                </TableCell>
                <TableCell className="text-right">
                  {isSpring ? (
                    <Input
                      type="number"
                      step="0.5"
                      value={earnedPractical}
                      onChange={(e) =>
                        setEarnedPractical(parseFloat(e.target.value) || 0)
                      }
                      className="ml-auto h-7 w-16 bg-background text-right text-sm"
                    />
                  ) : (
                    basePractical.toFixed(1)
                  )}
                </TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {currentTermCredits.practical.toFixed(1)}
                </TableCell>
                <TableCell className="bg-primary/5 text-right font-semibold text-primary">
                  {totalPractical.toFixed(1)}
                </TableCell>
                <TableCell className="text-right text-sm text-muted-foreground">
                  {reqPractical}
                </TableCell>
              </TableRow>

              {/* 特別研究 */}
              <TableRow>
                <TableCell className="font-medium text-muted-foreground">
                  特別研究
                </TableCell>
                <TableCell className="text-right">
                  {isSpring ? (
                    <Input
                      type="number"
                      step="0.5"
                      value={earnedResearch}
                      onChange={(e) =>
                        setEarnedResearch(parseFloat(e.target.value) || 0)
                      }
                      className="ml-auto h-7 w-16 bg-background text-right text-sm"
                    />
                  ) : (
                    baseResearch.toFixed(1)
                  )}
                </TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {currentTermCredits.research.toFixed(1)}
                </TableCell>
                <TableCell className="bg-primary/5 text-right font-semibold text-primary">
                  {totalResearch.toFixed(1)}
                </TableCell>
                <TableCell className="text-right text-sm text-muted-foreground">
                  {reqResearch}
                </TableCell>
              </TableRow>

              {/* 小計 */}
              <TableRow className="bg-muted/30">
                <TableCell className="font-semibold text-muted-foreground">
                  小計
                </TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {(basePractical + baseResearch).toFixed(1)}
                </TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {(
                    currentTermCredits.practical + currentTermCredits.research
                  ).toFixed(1)}
                </TableCell>
                <TableCell className="bg-primary/10 text-right font-bold text-primary">
                  {totalSubtotal.toFixed(1)}
                </TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {reqSubtotal}
                </TableCell>
              </TableRow>

              {/* 授業科目 */}
              <TableRow>
                <TableCell className="font-medium text-muted-foreground">
                  授業科目
                </TableCell>
                <TableCell className="text-right">
                  {isSpring ? (
                    <Input
                      type="number"
                      step="0.5"
                      value={earnedLectures}
                      onChange={(e) =>
                        setEarnedLectures(parseFloat(e.target.value) || 0)
                      }
                      className="ml-auto h-7 w-16 bg-background text-right text-sm"
                    />
                  ) : (
                    baseLectures.toFixed(1)
                  )}
                </TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {currentTermCredits.lectures.toFixed(1)}
                </TableCell>
                <TableCell className="bg-primary/5 text-right font-semibold text-primary">
                  {totalLectures.toFixed(1)}
                </TableCell>
                <TableCell className="text-right text-sm text-muted-foreground">
                  {reqLectures}以上
                </TableCell>
              </TableRow>

              {/* 合計 */}
              <TableRow className="border-t-2 bg-muted/50 hover:bg-muted/50">
                <TableCell className="font-bold">総合計</TableCell>
                <TableCell className="text-right font-bold">
                  {(basePractical + baseResearch + baseLectures).toFixed(1)}
                </TableCell>
                <TableCell className="text-right font-bold">
                  {(
                    currentTermCredits.practical +
                    currentTermCredits.research +
                    currentTermCredits.lectures
                  ).toFixed(1)}
                </TableCell>
                <TableCell className="bg-primary/20 text-right text-base font-bold text-primary">
                  {grandTotal.toFixed(1)}
                </TableCell>
                <TableCell className="text-right font-bold">
                  {reqTotal}以上
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div className="mt-auto space-y-1.5 border-t bg-muted/20 p-4 text-xs text-muted-foreground">
          <p className="flex items-start gap-1">
            <span className="mt-0.5">•</span>
            <span>
              他領域から <strong className="text-foreground">4単位以上</strong>{" "}
              修得することを推奨します。
            </span>
          </p>
          <p className="flex items-start gap-1">
            <span className="mt-0.5 text-primary">•</span>
            <span>
              英語での開講科目から{" "}
              <strong className="text-foreground">2単位以上</strong>{" "}
              修得することを推奨します。
            </span>
          </p>
          {isNuclear && (
            <p className="flex items-start gap-1 font-medium text-amber-600 dark:text-amber-500">
              <span className="mt-0.5">•</span>
              <span>
                共同原子力専攻の要件（実習・演習2単位、小計10単位、授業科目20単位以上）が適用されています。
              </span>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
