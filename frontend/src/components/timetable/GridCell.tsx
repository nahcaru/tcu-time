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
        "h-20 sm:h-24 p-1 sm:p-2 border rounded-md flex items-center justify-center text-center text-xs sm:text-sm transition-colors cursor-pointer",
        state === "empty" && "bg-transparent hover:bg-muted/50 border-dashed border-muted-foreground/30",
        state === "single" && "bg-secondary text-secondary-foreground hover:bg-secondary/80 border-transparent shadow-sm",
        state === "conflict" && "bg-destructive text-destructive-foreground hover:bg-destructive/90 border-transparent font-medium shadow-sm"
      )}
    >
      {state === "single" && (
        <span className="line-clamp-2 md:line-clamp-3">{courseName}</span>
      )}
      {state === "conflict" && <span>重複</span>}
    </div>
  )
}
