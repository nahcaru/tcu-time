import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

const DEMO_EXTRACTIONS = [
  { id: 1, department: "02機械", status: "pending", date: "2025-04-01 10:00" },
  { id: 2, department: "01機械", status: "completed", date: "2025-04-01 09:30" },
  { id: 3, department: "09情報", status: "error", date: "2025-04-01 09:00" },
]

export function ExtractionList() {
  return (
    <div className="rounded-md border bg-card overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>専攻</TableHead>
            <TableHead>ステータス</TableHead>
            <TableHead>実行日時</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {DEMO_EXTRACTIONS.map((ext) => (
            <TableRow key={ext.id}>
              <TableCell className="font-medium">{ext.department}</TableCell>
              <TableCell>
                {ext.status === "pending" && <Badge variant="outline" className="text-yellow-600 border-yellow-600">承認待ち</Badge>}
                {ext.status === "completed" && <Badge variant="outline" className="text-green-600 border-green-600">完了</Badge>}
                {ext.status === "error" && <Badge variant="destructive">エラー</Badge>}
              </TableCell>
              <TableCell className="text-muted-foreground text-xs whitespace-nowrap">{ext.date}</TableCell>
              <TableCell className="text-right">
                <a href="#" className="text-sm font-medium text-primary hover:underline whitespace-nowrap">
                  詳細を見る
                </a>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
