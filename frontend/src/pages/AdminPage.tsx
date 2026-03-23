import { ExtractionList } from "@/components/admin/ExtractionList"
import { PageHeader } from "@/components/layout/PageHeader"

export function AdminPage() {
  return (
    <div className="relative flex min-h-full flex-col pb-6">
      <PageHeader title="管理パネル" />

      <div className="flex min-h-full w-full flex-1 flex-col px-4 pt-14 md:px-6 md:pt-0">
        <div className="flex flex-col gap-6 pt-6">
          <p className="text-sm text-muted-foreground">
            抽出タスクの確認と承認を行います。承認された内容が授業データに反映されます。
          </p>
          <ExtractionList />
        </div>
      </div>
    </div>
  )
}
