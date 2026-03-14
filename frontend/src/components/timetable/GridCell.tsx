import { cn } from "@/lib/utils"

export type CellState = "empty" | "single" | "conflict"

export interface GridCellProps {
  state: CellState
  courseName?: string
  onClick?: () => void
}

export function GridCell({ state, courseName, onClick }: GridCellProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "flex h-10 cursor-pointer items-center justify-center rounded-md border p-1 text-center text-xs transition-colors sm:h-12 sm:p-2 sm:text-sm",
        state === "empty" &&
          "border-dashed border-muted-foreground/30 bg-transparent hover:bg-muted/50",
        state === "single" &&
          "border-transparent bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        state === "conflict" &&
          "text-destructive-foreground border-transparent bg-destructive font-medium shadow-sm hover:bg-destructive/90"
      )}
    >
      {state === "single" && (
        <span className="line-clamp-2 md:line-clamp-3">{courseName}</span>
      )}
      {state === "conflict" && <span>重複</span>}
    </div>
  )
}
