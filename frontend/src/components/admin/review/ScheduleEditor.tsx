import {
  VALID_DAYS,
  VALID_PERIODS,
  type RawSchedule,
} from "@/lib/approvalService"
import {
  FormSectionHeader,
  FormSelect,
  AddButton,
  DeleteButton,
} from "./FormControls"
import { cn } from "@/lib/utils"

interface ScheduleEditorProps {
  label?: string
  schedules: RawSchedule[]
  onChange: (schedules: RawSchedule[]) => void
  className?: string
  hideHeader?: boolean
}

export function ScheduleEditor({
  label = "曜日・時限",
  schedules,
  onChange,
  className,
  hideHeader = false,
}: ScheduleEditorProps) {
  const updateSlot = (index: number, patch: Partial<RawSchedule>) => {
    const next = [...schedules]
    next[index] = { ...next[index], ...patch }
    onChange(next)
  }

  const removeSlot = (index: number) => {
    onChange(schedules.filter((_, idx) => idx !== index))
  }

  const addSlot = () => {
    onChange([...schedules, { day: "月", period: 1 }])
  }

  return (
    <div className={cn("space-y-2", className)}>
      {!hideHeader && (
        <FormSectionHeader
          title={label}
          count={schedules.length}
        />
      )}
      {schedules.length > 0 && (
        <div className="space-y-1.5">
          {schedules.map((s, si) => (
            <div key={si} className="flex items-end gap-2">
              <FormSelect
                label="曜日"
                value={s.day}
                options={VALID_DAYS}
                onChange={(v) => updateSlot(si, { day: v })}
                className="w-24 shrink-0"
              />
              <FormSelect
                label="時限"
                value={s.period}
                options={VALID_PERIODS}
                optionLabels={Object.fromEntries(
                  VALID_PERIODS.map((p) => [String(p), `${p}限`])
                )}
                onChange={(v) => updateSlot(si, { period: Number(v) || 1 })}
                className="w-24 shrink-0"
              />
              <DeleteButton onClick={() => removeSlot(si)} />
            </div>
          ))}
        </div>
      )}
      <AddButton onClick={addSlot} label="コマを追加" />
    </div>
  )
}
