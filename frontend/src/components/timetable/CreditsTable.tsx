import { useState, useMemo } from "react"
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
  const [selectedTarget, setSelectedTarget] = useState<string>("02")

  const isNuclear = selectedTarget === "06"

  // Requirements
  const reqPractical = isNuclear ? 2 : 4
  const reqResearch = 8
  const reqSubtotal = isNuclear ? 10 : 12
  const reqLectures = isNuclear ? 20 : 18
  const reqTotal = 30

  // Editable earned credits (entered by user for 前期)
  const [earnedPractical, setEarnedPractical] = useState(0)
  const [earnedResearch, setEarnedResearch] = useState(0)
  const [earnedLectures, setEarnedLectures] = useState(0)

  // Compute term credits from enrolled courses
  const termCredits = useMemo(() => {
    const prefix = isSpring ? "前" : "後"
    let lectures = 0

    for (const course of enrolledCourses) {
      // Check if course has schedules in this term
      const inTerm = course.schedules.some((s) => s.term.startsWith(prefix))
      if (!inTerm) continue

      const credits = course.course_metadata[0]?.credits ?? 0
      const category = course.course_metadata[0]?.category

      if (category === "授業科目" || !category) {
        lectures += credits
      }
    }

    return { lectures }
  }, [enrolledCourses, isSpring])

  const totalPractical = earnedPractical
  const totalResearch = earnedResearch
  const totalSubtotal = totalPractical + totalResearch
  const totalLectures = earnedLectures + termCredits.lectures
  const grandTotal = totalSubtotal + totalLectures

  return (
    <div className="rounded-xl border bg-card flex flex-col h-full overflow-hidden shadow-sm">
      <div className="p-4 border-b flex items-center justify-between gap-4 bg-muted/20">
        <h3 className="font-semibold">単位修得状況</h3>
        <Select value={selectedTarget} onValueChange={setSelectedTarget}>
          <SelectTrigger className="w-[180px] h-8 text-sm bg-background">
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

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[120px] whitespace-nowrap">
                項目
              </TableHead>
              <TableHead className="text-right whitespace-nowrap">
                修得済
              </TableHead>
              <TableHead className="text-right whitespace-nowrap">
                {termType}取得
              </TableHead>
              <TableHead className="text-right whitespace-nowrap bg-muted/10 font-bold text-foreground">
                合計
              </TableHead>
              <TableHead className="text-right whitespace-nowrap text-muted-foreground w-[80px]">
                要件
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
                    className="w-16 ml-auto h-7 text-right bg-background text-sm"
                  />
                ) : (
                  earnedPractical.toFixed(1)
                )}
              </TableCell>
              <TableCell className="text-right font-medium text-sm">
                0.0
              </TableCell>
              <TableCell className="text-right font-semibold bg-primary/5 text-primary">
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
                    className="w-16 ml-auto h-7 text-right bg-background text-sm"
                  />
                ) : (
                  earnedResearch.toFixed(1)
                )}
              </TableCell>
              <TableCell className="text-right font-medium text-sm">
                0.0
              </TableCell>
              <TableCell className="text-right font-semibold bg-primary/5 text-primary">
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
              <TableCell className="text-right font-medium text-sm">
                {(earnedPractical + earnedResearch).toFixed(1)}
              </TableCell>
              <TableCell className="text-right font-medium text-sm">
                0.0
              </TableCell>
              <TableCell className="text-right font-bold bg-primary/10 text-primary">
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
                    className="w-16 ml-auto h-7 text-right bg-background text-sm"
                  />
                ) : (
                  earnedLectures.toFixed(1)
                )}
              </TableCell>
              <TableCell className="text-right font-medium text-sm">
                {termCredits.lectures.toFixed(1)}
              </TableCell>
              <TableCell className="text-right font-semibold bg-primary/5 text-primary">
                {totalLectures.toFixed(1)}
              </TableCell>
              <TableCell className="text-right text-sm text-muted-foreground">
                {reqLectures}以上
              </TableCell>
            </TableRow>

            {/* 合計 */}
            <TableRow className="bg-muted/50 hover:bg-muted/50 border-t-2">
              <TableCell className="font-bold">総合計</TableCell>
              <TableCell className="text-right font-bold">
                {(earnedPractical + earnedResearch + earnedLectures).toFixed(1)}
              </TableCell>
              <TableCell className="text-right font-bold">
                {termCredits.lectures.toFixed(1)}
              </TableCell>
              <TableCell className="text-right font-bold bg-primary/20 text-primary text-base">
                {grandTotal.toFixed(1)}
              </TableCell>
              <TableCell className="text-right font-bold">
                {reqTotal}以上
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <div className="p-4 bg-muted/20 mt-auto border-t text-xs text-muted-foreground space-y-1.5">
        <p className="flex items-start gap-1">
          <span className="text-primary mt-0.5">•</span>
          <span>
            他領域から{" "}
            <strong className="text-foreground">4単位以上</strong>{" "}
            修得することを推奨します。
          </span>
        </p>
        <p className="flex items-start gap-1">
          <span className="text-primary mt-0.5">•</span>
          <span>
            英語での開講科目から{" "}
            <strong className="text-foreground">2単位以上</strong>{" "}
            修得することを推奨します。
          </span>
        </p>
        {isNuclear && (
          <p className="flex items-start gap-1 text-amber-600 dark:text-amber-500 font-medium">
            <span className="mt-0.5">•</span>
            <span>
              共同原子力専攻の要件（実習・演習2単位、小計10単位、授業科目20単位以上）が適用されています。
            </span>
          </p>
        )}
      </div>
    </div>
  )
}
