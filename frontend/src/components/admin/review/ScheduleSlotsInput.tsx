import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { IconPlus, IconX } from "@tabler/icons-react"
import { VALID_DAYS, VALID_PERIODS, type RawSchedule } from "@/lib/approvalService"

interface ScheduleSlotsInputProps {
  label: string
  schedules: RawSchedule[]
  onChange: (schedules: RawSchedule[]) => void
  className?: string
}

export function ScheduleSlotsInput({
  label,
  schedules,
  onChange,
  className,
}: ScheduleSlotsInputProps) {
  const [day, setDay] = useState<string>("月")
  const [period, setPeriod] = useState<number>(1)

  const addSlot = () => {
    // Avoid exact duplicate slot
    if (schedules.some((s) => s.day === day && s.period === period)) {
      return
    }
    onChange([...schedules, { day, period }])
  }

  const removeSlot = (index: number) => {
    onChange(schedules.filter((_, i) => i !== index))
  }

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
          {label}
        </span>
        {schedules.length > 0 && (
          <span className="text-[10px] text-muted-foreground">
            {schedules.length} コマ
          </span>
        )}
      </div>

      <div className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-input bg-background/50 p-1.5 text-sm shadow-xs transition-colors dark:bg-input/30">
        {schedules.length === 0 ? (
          <span className="px-1 text-xs text-muted-foreground/60">
            コマ未登録
          </span>
        ) : (
          schedules.map((s, idx) => (
            <Badge
              key={`${s.day}-${s.period}-${idx}`}
              variant="outline"
              className="flex items-center gap-1 bg-background py-0.5 pr-1 pl-2 text-xs font-medium"
            >
              <span>{s.day}{s.period}限</span>
              <button
                type="button"
                onClick={() => removeSlot(idx)}
                className="rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none"
                title="削除"
              >
                <IconX className="size-3" />
              </button>
            </Badge>
          ))
        )}

        <div className="flex items-center gap-1 ml-auto shrink-0">
          <select
            value={day}
            onChange={(e) => setDay(e.target.value)}
            className="h-6 rounded border border-input bg-background px-1 text-xs"
          >
            {VALID_DAYS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <select
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
            className="h-6 rounded border border-input bg-background px-1 text-xs"
          >
            {VALID_PERIODS.map((p) => (
              <option key={p} value={p}>
                {p}限
              </option>
            ))}
          </select>
          <Button
            type="button"
            size="xs"
            variant="ghost"
            onClick={addSlot}
            className="h-6 px-1.5 text-xs text-primary hover:bg-primary/10"
          >
            <IconPlus className="size-3 mr-0.5" />
            追加
          </Button>
        </div>
      </div>
    </div>
  )
}
