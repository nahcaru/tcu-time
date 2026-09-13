import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: {
    label: "処理中",
    className:
      "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  },
  extracted: {
    label: "承認待ち",
    className:
      "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400",
  },
  approved: {
    label: "承認済み",
    className:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
}

export function StatusBadge({
  status,
  className,
}: {
  status?: string | null
  className?: string
}) {
  const config = STATUS_CONFIG[status ?? ""] ?? {
    label: status || "不明",
    className: "border-border bg-muted text-muted-foreground",
  }

  return (
    <Badge variant="outline" className={cn(config.className, className)}>
      {config.label}
    </Badge>
  )
}
