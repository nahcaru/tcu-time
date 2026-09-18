import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function ExtractionTableSkeleton() {
  return (
    <div className="space-y-4">
      {/* Filter tabs skeleton */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Skeleton className="h-9 w-72 rounded-lg" />
        <Skeleton className="h-8 w-44 rounded-md" />
      </div>

      {/* Table skeleton */}
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
                PDF URL
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
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-4 w-4 rounded-sm" />
                    <Skeleton className="h-4 w-20" />
                  </div>
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-10" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-12" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-32" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-5 w-16 rounded-full" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-24" />
                </TableCell>
                <TableCell className="text-right">
                  <Skeleton className="ml-auto h-8 w-16 rounded-md" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

export function ReviewPageSkeleton() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {/* Split layout */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Left PDF skeleton */}
        <Card className="flex h-full min-h-[400px] flex-col gap-0 overflow-hidden py-0 shadow-xs">
          <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-2.5">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-4 w-20" />
          </div>
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6">
            <Skeleton className="h-12 w-12 rounded-xl" />
            <Skeleton className="h-4 w-40" />
          </div>
        </Card>

        {/* Right editor cards skeleton */}
        <Card className="flex h-full flex-col gap-0 overflow-hidden py-0 shadow-xs">
          <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-2.5">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <div className="flex-1 space-y-3 overflow-hidden p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card
                key={i}
                className="gap-0 overflow-hidden rounded-xl border py-0 shadow-xs"
              >
                <div className="flex items-center gap-3 p-3 sm:px-4">
                  <Skeleton className="h-4 w-4 shrink-0 rounded-sm" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-4 w-4 shrink-0 rounded-sm" />
                </div>
              </Card>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
