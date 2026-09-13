import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Kbd } from "@/components/ui/kbd"

interface ShortcutItem {
  keys: string[]
  desc: string
  operator?: "+" | "/"
}

const SHORTCUTS: ShortcutItem[] = [
  { keys: ["j", "↓"], desc: "次の項目へ移動", operator: "/" },
  { keys: ["k", "↑"], desc: "前の項目へ移動", operator: "/" },
  {
    keys: ["Space", "x"],
    desc: "現在の項目の確認（チェック）を切り替え",
    operator: "/",
  },
  { keys: ["Enter", "o"], desc: "現在の項目の詳細を開閉", operator: "/" },
  { keys: ["a"], desc: "全選択 / 全選択解除の切り替え" },
  { keys: ["⌘", "Enter"], desc: "承認して反映", operator: "+" },
  { keys: ["Esc"], desc: "一覧画面へ戻る" },
  { keys: ["?"], desc: "ショートカット一覧を表示" },
]

export function KeyboardShortcutsDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>キーボードショートカット</DialogTitle>
          <DialogDescription>
            レビューを素早く行うための操作です。入力フォーム入力中以外に有効です。
          </DialogDescription>
        </DialogHeader>
        <div className="divide-y divide-border text-sm pt-2">
          {SHORTCUTS.map((s) => (
            <div
              key={s.desc}
              className="flex items-center justify-between py-2.5"
            >
              <span className="text-muted-foreground">{s.desc}</span>
              <div className="flex items-center gap-1">
                {s.keys.map((k, ki) => (
                  <span key={ki} className="flex items-center gap-1">
                    {ki > 0 && s.operator && (
                      <span className="text-xs text-muted-foreground">
                        {s.operator}
                      </span>
                    )}
                    <Kbd className="font-mono text-xs border shadow-xs">
                      {k}
                    </Kbd>
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
