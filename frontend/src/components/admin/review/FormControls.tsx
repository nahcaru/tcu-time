import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { IconPlus, IconTrash } from "@tabler/icons-react"

export function FormField({
  label,
  value,
  onChange,
  placeholder,
  readOnly = false,
  className,
}: {
  label: string
  value: string | number
  onChange?: (v: string) => void
  placeholder?: string
  readOnly?: boolean
  className?: string
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
      {readOnly ? (
        <span className="text-sm font-medium">{value}</span>
      ) : (
        <Input
          className="h-8 bg-background/50 text-sm"
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange?.(e.target.value)}
        />
      )}
    </div>
  )
}

export function FormSelect({
  label,
  value,
  options,
  optionLabels,
  onChange,
  className,
}: {
  label: string
  value: string | number
  options: readonly (string | number)[]
  optionLabels?: Record<string, string>
  onChange: (v: string) => void
  className?: string
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
      <select
        className="flex h-8 w-full items-center justify-between rounded-md border border-input bg-background/50 px-2 py-1 text-sm shadow-xs transition-colors focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30"
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={String(opt)} value={String(opt)}>
            {optionLabels?.[String(opt)] ?? opt}
          </option>
        ))}
      </select>
    </div>
  )
}

export function FormSectionHeader({
  title,
  count,
}: {
  title: string
  count?: number
}) {
  return (
    <div className="flex items-center gap-2 border-t border-border/50 pt-2">
      <span className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
        {title}
      </span>
      {count !== undefined && (
        <Badge variant="outline" className="h-4 px-1 text-[10px] font-normal">
          {count}
        </Badge>
      )}
    </div>
  )
}

export function AddButton({
  onClick,
  label = "追加",
}: {
  onClick: () => void
  label?: string
}) {
  const cleanLabel = label.replace(/^\+\s*/, "")
  return (
    <Button
      type="button"
      variant="outline"
      size="xs"
      onClick={onClick}
      className="gap-1 text-xs border-dashed text-primary hover:text-primary hover:bg-primary/5"
    >
      <IconPlus className="size-3" />
      <span>{cleanLabel}</span>
    </Button>
  )
}

export function DeleteButton({
  onClick,
  title = "削除",
}: {
  onClick: () => void
  title?: string
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      onClick={onClick}
      className="shrink-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
      title={title}
    >
      <IconTrash className="size-3.5" />
    </Button>
  )
}
