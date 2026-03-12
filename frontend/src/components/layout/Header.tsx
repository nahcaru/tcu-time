import { IconUser, IconSun, IconMoon } from "@tabler/icons-react"
import { Link } from "react-router"
import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"

export function Header() {
  const { theme, setTheme } = useTheme()

  return (
    <header className="supports-backdrop-filter:bg-background/60 sticky top-0 z-50 flex h-14 items-center justify-between border-b bg-background/95 px-4 backdrop-blur md:hidden">
      <div className="text-lg font-bold">TiME</div>
      <div className="flex items-center gap-2">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? <IconMoon className="h-5 w-5" /> : <IconSun className="h-5 w-5" />}
        </Button>
        <Button variant="ghost" size="icon" asChild>
          <Link to="/profile">
            <IconUser className="h-5 w-5" />
          </Link>
        </Button>
      </div>
    </header>
  )
}
