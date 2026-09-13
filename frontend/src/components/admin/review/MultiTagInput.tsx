import { useState, type KeyboardEvent, type ClipboardEvent } from "react"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { IconPlus, IconX } from "@tabler/icons-react"

interface MultiTagInputProps {
  label: string
  values: string[]
  onChange: (values: string[]) => void
  placeholder?: string
  className?: string
}

export function MultiTagInput({
  label,
  values,
  onChange,
  placeholder = "入力して Enter...",
  className,
}: MultiTagInputProps) {
  const [inputValue, setInputValue] = useState("")

  const addValues = (raw: string) => {
    const split = raw
      .split(/[,、\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (split.length === 0) return

    // Append unique or all values
    const next = [...values, ...split]
    onChange(next)
    setInputValue("")
  }

  const removeValue = (index: number) => {
    onChange(values.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === "," || e.key === "、") {
      e.preventDefault()
      addValues(inputValue)
    } else if (e.key === "Backspace" && !inputValue && values.length > 0) {
      removeValue(values.length - 1)
    }
  }

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    const text = e.clipboardData.getData("text")
    if (text.includes(",") || text.includes("、") || text.includes("\n")) {
      e.preventDefault()
      addValues(text)
    }
  }

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
          {label}
        </span>
        {values.length > 0 && (
          <span className="text-[10px] text-muted-foreground">
            {values.length} 件
          </span>
        )}
      </div>

      <div className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-input bg-background/50 p-1.5 text-sm shadow-xs transition-colors focus-within:ring-1 focus-within:ring-ring dark:bg-input/30">
        {values.map((val, idx) => (
          <Badge
            key={`${val}-${idx}`}
            variant="secondary"
            className="flex items-center gap-1 py-0.5 pr-1 pl-2 text-xs font-normal"
          >
            <span className="truncate max-w-[200px]">{val}</span>
            <button
              type="button"
              onClick={() => removeValue(idx)}
              className="rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none"
              title="削除"
            >
              <IconX className="size-3" />
            </button>
          </Badge>
        ))}

        <div className="flex flex-1 items-center gap-1 min-w-[120px]">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={values.length === 0 ? placeholder : "+ 追加..."}
            className="h-7 border-0 bg-transparent px-1.5 text-xs shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60"
          />
          {inputValue.trim() && (
            <Button
              type="button"
              size="xs"
              variant="ghost"
              onClick={() => addValues(inputValue)}
              className="h-6 px-1.5 text-xs"
            >
              <IconPlus className="size-3 mr-0.5" />
              追加
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
