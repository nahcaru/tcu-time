import { ExtractionList } from "@/components/admin/ExtractionList"
import { ReviewPanel } from "@/components/admin/ReviewPanel"

export function AdminPage() {
  return (
    <div className="flex flex-col h-full bg-background md:-mt-6 md:-mx-6 md:p-6 lg:p-0">
      <div className="flex-1 lg:p-6 lg:pl-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight">管理画面</h1>
          <p className="text-muted-foreground">シラバス抽出タスクのステータス管理と承認</p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold mb-4">最近の抽出処理</h2>
            <ExtractionList />
          </div>
          <div className="lg:col-span-1">
            <h2 className="text-lg font-semibold mb-4">レビュー</h2>
            <ReviewPanel />
          </div>
        </div>
      </div>
    </div>
  )
}
