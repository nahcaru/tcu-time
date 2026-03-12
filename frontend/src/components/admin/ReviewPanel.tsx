import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function ReviewPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>承認パネル</CardTitle>
        <CardDescription>
          現在選択されている抽出結果の確認と本番反映を行います。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-md border p-4 bg-muted/20">
          <h4 className="font-medium mb-2">02機械 - 抽出サマリー</h4>
          <ul className="text-sm space-y-1 text-muted-foreground">
            <li>新規追加: 12件</li>
            <li>更新: 3件</li>
            <li>削除: 0件</li>
          </ul>
        </div>
      </CardContent>
      <CardFooter className="flex justify-end gap-2 flex-wrap">
        <Button variant="outline" className="flex-1 sm:flex-none">拒否する</Button>
        <Button className="flex-1 sm:flex-none">本番へ反映を承認</Button>
      </CardFooter>
    </Card>
  )
}
