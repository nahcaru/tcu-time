import { Link, useLocation } from "react-router"
import { IconList, IconTableFilled } from "@tabler/icons-react"
import { cn } from "@/lib/utils"

export function BottomNav() {
  const location = useLocation()

  return (
    <nav className="fixed right-0 bottom-0 left-0 z-50 flex h-16 border-t bg-background md:hidden">
      <Link
        to="/"
        className={cn(
          "flex flex-1 flex-col items-center justify-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground",
          location.pathname === "/" && "text-primary"
        )}
      >
        <IconList className="h-6 w-6" />
        <span>科目一覧</span>
      </Link>
      <Link
        to="/timetable"
        className={cn(
          "flex flex-1 flex-col items-center justify-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground",
          location.pathname === "/timetable" && "text-primary"
        )}
      >
        <IconTableFilled className="h-6 w-6" />
        <span>時間割</span>
      </Link>
    </nav>
  )
}
