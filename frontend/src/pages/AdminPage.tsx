import { ExtractionList } from "@/components/admin/ExtractionList"

export function AdminPage() {
  return (
    <div className="container py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">管理パネル</h1>
        <p className="text-sm text-muted-foreground">
          抽出タスクの確認と承認を行います。承認された内容が授業データに反映されます。
        </p>
      </div>
      <ExtractionList />
    </div>
  )
}
