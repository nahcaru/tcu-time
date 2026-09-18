import {
  FormField,
  FormSectionHeader,
  AddButton,
  DeleteButton,
} from "./FormControls"
import { cn } from "@/lib/utils"

interface InstructorsEditorProps {
  label?: string
  instructors: string[]
  onChange: (instructors: string[]) => void
  className?: string
  hideHeader?: boolean
}

export function InstructorsEditor({
  label = "担当者",
  instructors,
  onChange,
  className,
  hideHeader = false,
}: InstructorsEditorProps) {
  const effectiveInstructors = instructors.length > 0 ? instructors : [""]

  const updateInstructor = (index: number, val: string) => {
    const next = [...effectiveInstructors]
    next[index] = val
    onChange(next)
  }

  const removeInstructor = (index: number) => {
    onChange(effectiveInstructors.filter((_, idx) => idx !== index))
  }

  const addInstructor = () => {
    onChange([...effectiveInstructors, ""])
  }

  return (
    <div className={cn("space-y-2", className)}>
      {!hideHeader && (
        <FormSectionHeader
          title={label}
          count={instructors.filter(Boolean).length}
        />
      )}
      <div className="space-y-1.5">
        {effectiveInstructors.map((instr, ii) => (
          <div key={ii} className="flex items-center gap-2">
            <FormField
              label=""
              value={instr}
              placeholder="教員名"
              onChange={(v) => updateInstructor(ii, v)}
              className="flex-1"
            />
            {effectiveInstructors.length > 1 && (
              <DeleteButton onClick={() => removeInstructor(ii)} />
            )}
          </div>
        ))}
      </div>
      <AddButton onClick={addInstructor} label="担当者を追加" />
    </div>
  )
}
