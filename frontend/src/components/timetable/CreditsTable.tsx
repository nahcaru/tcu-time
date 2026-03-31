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

type EarnedCreditsValue = {
  practical?: number | string | null
  research?: number | string | null
  lectures?: number | string | null
}

function isEarnedCreditsValue(value: unknown): value is EarnedCreditsValue {
  return typeof value === "object" && value !== null
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
    const credits = isEarnedCreditsValue(settings?.earned_credits)
      ? settings.earned_credits
      : undefined
    const parse = (v: number | string | null | undefined) =>
      typeof v === "number" ? v : typeof v === "string" ? parseFloat(v) || 0 : 0

    return {
      practical: parse(credits?.practical),
      research: parse(credits?.research),
      lectures: parse(credits?.lectures),
    }
  }, [settings?.earned_credits])

  // Editable earned credits
  const [earnedPractical, setEarnedPractical] = useState("0")
  const [earnedResearch, setEarnedResearch] = useState("0")
  const [earnedLectures, setEarnedLectures] = useState("0")

  // Sync from settings to local state
  useEffect(() => {
    setEarnedPractical(earnedCredits.practical.toString())
    setEarnedResearch(earnedCredits.research.toString())
    setEarnedLectures(earnedCredits.lectures.toString())
  }, [earnedCredits])

  // Debounce updates to settings
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      const current = {
        practical: parseFloat(earnedPractical) || 0,
        research: parseFloat(earnedResearch) || 0,
        lectures: parseFloat(earnedLectures) || 0,
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

  const normalizeTargetCode = (code: string) => code.replace(/^0+/, "") || "0"
  const isEnglishNamedCourse = (name: string) =>
    /^[A-Za-z0-9\s!-/:-@[-`{-~]+$/.test(name) &&
    !/[ぁ-ゖァ-ヺ一-龯々]/.test(name)

  // Compute term credits safely for all categories
  const computedCredits = useMemo(() => {
    const spring = { practical: 0, research: 0, lectures: 0 }
    const fall = { practical: 0, research: 0, lectures: 0 }

    for (const course of enrolledCourses) {
      const credits = course.course_metadata[0]?.credits ?? 0
      const category = course.course_metadata[0]?.category

      const hasSpring = course.term?.startsWith("前") ?? false
      const hasFall = course.term?.startsWith("後") ?? false
      const isAnnual = course.term === "通年"

      // Define bucket based on category
      let bucket: "practical" | "research" | "lectures" = "lectures"
      if (category === "実習・演習") bucket = "practical"
      else if (category === "特別研究") bucket = "research"

      if (hasSpring) spring[bucket] += credits
      if (hasFall) fall[bucket] += credits
      if (isAnnual) fall[bucket] += credits
    }
    return { spring, fall }
  }, [enrolledCourses])

  // Current term credits to display on column 3
  const currentTermCredits = isSpring
    ? computedCredits.spring
    : computedCredits.fall

  // First column base values (with Spring addition if checking Fall view)
  const basePractical =
    (parseFloat(earnedPractical) || 0) +
    (isSpring ? 0 : computedCredits.spring.practical)
  const baseResearch =
    (parseFloat(earnedResearch) || 0) +
    (isSpring ? 0 : computedCredits.spring.research)
  const baseLectures =
    (parseFloat(earnedLectures) || 0) +
    (isSpring ? 0 : computedCredits.spring.lectures)

  // Totals for Column 4 (Grand total in that row)
  const totalPractical = basePractical + currentTermCredits.practical
  const totalResearch = baseResearch + currentTermCredits.research
  const totalLectures = baseLectures + currentTermCredits.lectures

  const totalSubtotal = totalPractical + totalResearch
  const grandTotal = totalSubtotal + totalLectures

  const recommendationProgress = useMemo(() => {
    const selectedTargetCode = normalizeTargetCode(selectedTarget)

    let otherField = 0
    let english = 0

    for (const course of enrolledCourses) {
      const credits = course.course_metadata[0]?.credits ?? 0

      if (credits <= 0) continue

      const hasOtherFieldTarget = course.course_targets.some(
        (target) =>
          normalizeTargetCode(target.target_code) !== selectedTargetCode
      )

      if (hasOtherFieldTarget) {
        otherField += credits
      }

      if (isEnglishNamedCourse(course.name)) {
        english += credits
      }
    }

    return { otherField, english }
  }, [enrolledCourses, selectedTarget])

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
                  {isSpring ? "前期" : "後期+通年"}
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
                      value={earnedPractical}
                      onChange={(e) => setEarnedPractical(e.target.value)}
                      className="h-7 w-16 bg-background text-center text-sm"
                      aria-invalid={
                        isNaN(Number(earnedPractical)) ? "true" : undefined
                      }
                    />
                  ) : (
                    String(basePractical)
                  )}
                </TableCell>
                <TableCell className="text-right text-sm font-medium text-muted-foreground">
                  {String(currentTermCredits.practical)}
                </TableCell>
                <TableCell className="bg-primary/10 text-right font-semibold text-muted-foreground">
                  {String(totalPractical)}
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
                      value={earnedResearch}
                      onChange={(e) => setEarnedResearch(e.target.value)}
                      className="h-7 w-16 bg-background text-center text-sm"
                      aria-invalid={
                        isNaN(Number(earnedResearch)) ? "true" : undefined
                      }
                    />
                  ) : (
                    String(baseResearch)
                  )}
                </TableCell>
                <TableCell className="text-right text-sm font-medium text-muted-foreground">
                  {String(currentTermCredits.research)}
                </TableCell>
                <TableCell className="bg-primary/10 text-right font-semibold text-muted-foreground">
                  {String(totalResearch)}
                </TableCell>
                <TableCell className="text-right text-sm text-muted-foreground">
                  {reqResearch}
                </TableCell>
              </TableRow>

              {/* 小計 */}
              <TableRow className="bg-muted/30">
                <TableCell className="font-semibold">小計</TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {String(basePractical + baseResearch)}
                </TableCell>
                <TableCell className="text-right text-sm font-medium">
                  {String(
                    currentTermCredits.practical + currentTermCredits.research
                  )}
                </TableCell>
                <TableCell className="bg-primary/20 text-right font-bold">
                  {String(totalSubtotal)}
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
                      value={earnedLectures}
                      onChange={(e) => setEarnedLectures(e.target.value)}
                      className="h-7 w-16 bg-background text-center text-sm"
                      aria-invalid={
                        isNaN(Number(earnedLectures)) ? "true" : undefined
                      }
                    />
                  ) : (
                    String(baseLectures)
                  )}
                </TableCell>
                <TableCell className="text-right text-sm font-medium text-muted-foreground">
                  {String(currentTermCredits.lectures)}
                </TableCell>
                <TableCell className="bg-primary/10 text-right font-semibold text-muted-foreground">
                  {String(totalLectures)}
                </TableCell>
                <TableCell className="text-right text-sm text-muted-foreground">
                  {reqLectures}以上
                </TableCell>
              </TableRow>

              {/* 合計 */}
              <TableRow className="border-t-2 bg-muted/50 hover:bg-muted/50">
                <TableCell className="font-bold">合計</TableCell>
                <TableCell className="text-right font-bold">
                  {String(basePractical + baseResearch + baseLectures)}
                </TableCell>
                <TableCell className="text-right font-bold">
                  {String(
                    currentTermCredits.practical +
                      currentTermCredits.research +
                      currentTermCredits.lectures
                  )}
                </TableCell>
                <TableCell className="bg-primary/30 text-right text-base font-bold">
                  {String(grandTotal)}
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
              修得することを推奨します
              <span className="ml-1 text-foreground">
                （現在{" "}
                <strong className="text-foreground">
                  {String(recommendationProgress.otherField)}単位
                </strong>
                ）
              </span>
            </span>
          </p>
          <p className="flex items-start gap-1">
            <span className="mt-0.5">•</span>
            <span>
              英語での開講科目から{" "}
              <strong className="text-foreground">2単位以上</strong>{" "}
              修得することを推奨します
              <span className="ml-1 text-foreground">
                （現在{" "}
                <strong className="text-foreground">
                  {String(recommendationProgress.english)}単位
                </strong>
                ）
              </span>
            </span>
          </p>
        </div>
      </div>
    </div>
  )
}
