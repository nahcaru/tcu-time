import { useState } from "react"
import { IconUser, IconSun, IconMoon, IconLogin } from "@tabler/icons-react"
import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/use-auth"
import { LoginDialog } from "@/components/auth/LoginDialog"
import { ProfileDialog } from "@/components/auth/ProfileDialog"
export function Header() {
  const { theme, setTheme } = useTheme()
  const { user } = useAuth()

  const [loginOpen, setLoginOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  return (
    <>
      <header className="fixed top-0 right-0 left-0 z-50 flex h-14 w-full items-center justify-between border-b bg-background/95 px-4 backdrop-blur supports-backdrop-filter:bg-background/75 md:hidden">
        <div className="text-lg font-bold">TCU-TIME</div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? (
              <IconMoon className="h-5 w-5" />
            ) : (
              <IconSun className="h-5 w-5" />
            )}
          </Button>

          {user ? (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setProfileOpen(true)}
            >
              <IconUser className="h-5 w-5" />
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLoginOpen(true)}
            >
              <IconLogin className="h-5 w-5" />
            </Button>
          )}
        </div>
      </header>

      <LoginDialog open={loginOpen} onOpenChange={setLoginOpen} />
      <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />
    </>
  )
}
