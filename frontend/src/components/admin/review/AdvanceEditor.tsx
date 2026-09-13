import type { AdvanceRawJson } from "@/lib/approvalService"
import { Card } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { AddButton, DeleteButton } from "./FormControls"
import { cn } from "@/lib/utils"

interface AdvanceEditorProps {
  raw: AdvanceRawJson
  onChange: (r: AdvanceRawJson) => void
  checkedSet: Set<number>
  onToggleCheck: (index: number, checked: boolean) => void
  activeIndex?: number | null
  onSelectIndex?: (index: number) => void
}

export function AdvanceEditor({
  raw,
  onChange,
  checkedSet,
  onToggleCheck,
  activeIndex,
  onSelectIndex,
}: AdvanceEditorProps) {
  const names = raw.names ?? []

  const updateName = (i: number, v: string) => {
    const next = [...names]
    next[i] = v
    onChange({ ...raw, names: next, count: next.length })
  }

  const addName = () => {
    onChange({ ...raw, names: [...names, ""], count: names.length + 1 })
  }

  const removeName = (i: number) => {
    const next = names.filter((_, idx) => idx !== i)
    onChange({ ...raw, names: next, count: next.length })
  }

  return (
    <div className="space-y-2">
      {names.map((name, i) => {
        const isChecked = checkedSet.has(i)
        const isActive = activeIndex === i
        return (
          <Card
            key={i}
            onClick={() => onSelectIndex?.(i)}
            className={cn(
              "flex flex-row items-center gap-3 p-2 shadow-xs transition-all sm:px-3 cursor-pointer",
              isActive && "ring-2 ring-primary ring-offset-2 ring-offset-background",
              isChecked
                ? "border-border/60 bg-card/60"
                : "border-border bg-card ring-1 ring-primary/20"
            )}
          >
            <Checkbox
              checked={isChecked}
              onCheckedChange={(c) => onToggleCheck(i, c === true)}
              aria-label={`#${i + 1} ${name || "科目名"}`}
            />
            <span className="w-6 shrink-0 font-mono text-xs text-muted-foreground">
              #{i + 1}
            </span>
            <Input
              className="h-8 flex-1 bg-background/50 text-sm"
              value={name}
              placeholder="先行履修の科目名を入力"
              onChange={(e) => updateName(i, e.target.value)}
            />
            <DeleteButton onClick={() => removeName(i)} />
          </Card>
        )
      })}
      <div className="pt-2">
        <AddButton onClick={addName} label="科目を新規追加" />
      </div>
    </div>
  )
}
