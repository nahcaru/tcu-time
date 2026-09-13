import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"

const SHORTCUTS = [
  { key: "j / ↓", desc: "次の項目へ移動" },
  { key: "k / ↑", desc: "前の項目へ移動" },
  { key: "Space / x", desc: "現在の項目の確認（チェック）を切り替え" },
  { key: "Enter / o", desc: "現在の項目の詳細を開閉" },
  { key: "a", desc: "全選択 / 全選択解除の切り替え" },
  { key: "⌘ + Enter", desc: "抽出データを承認して反映" },
  { key: "Esc", desc: "一覧画面へ戻る" },
  { key: "?", desc: "ショートカット一覧を表示" },
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
              key={s.key}
              className="flex items-center justify-between py-2.5"
            >
              <span className="text-muted-foreground">{s.desc}</span>
              <kbd className="px-2 py-0.5 rounded bg-muted font-mono text-xs font-semibold border shadow-xs">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
