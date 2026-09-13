import { type RawTarget } from "@/lib/approvalService"
import {
  FormField,
  FormSectionHeader,
  AddButton,
  DeleteButton,
} from "./FormControls"
import { cn } from "@/lib/utils"

interface TargetsEditorProps {
  label?: string
  targets: RawTarget[]
  onChange: (targets: RawTarget[]) => void
  className?: string
  hideHeader?: boolean
}

export function TargetsEditor({
  label = "履修対象",
  targets,
  onChange,
  className,
  hideHeader = false,
}: TargetsEditorProps) {
  const updateTarget = (index: number, patch: Partial<RawTarget>) => {
    const next = [...targets]
    next[index] = { ...next[index], ...patch }
    onChange(next)
  }

  const removeTarget = (index: number) => {
    onChange(targets.filter((_, idx) => idx !== index))
  }

  const addTarget = () => {
    onChange([...targets, { target_code: "", target_name: "", note: "" }])
  }

  return (
    <div className={cn("space-y-2", className)}>
      {!hideHeader && (
        <FormSectionHeader
          title={label}
          count={targets.length}
        />
      )}
      {targets.length > 0 && (
        <div className="space-y-2">
          {targets.map((t, ti) => (
            <div
              key={ti}
              className="grid grid-cols-1 items-end gap-2 rounded-lg border bg-muted/20 p-2.5 sm:grid-cols-3"
            >
              <FormField
                label="コード"
                value={t.target_code}
                placeholder="専修コード"
                onChange={(v) => updateTarget(ti, { target_code: v })}
              />
              <FormField
                label="名称"
                value={t.target_name}
                placeholder="専攻・コース名"
                onChange={(v) => updateTarget(ti, { target_name: v })}
              />
              <div className="flex items-end gap-1.5">
                <FormField
                  label="備考"
                  value={t.note ?? ""}
                  placeholder="備考"
                  onChange={(v) => updateTarget(ti, { note: v })}
                  className="flex-1"
                />
                <DeleteButton onClick={() => removeTarget(ti)} />
              </div>
            </div>
          ))}
        </div>
      )}
      <AddButton onClick={addTarget} label="対象を追加" />
    </div>
  )
}
