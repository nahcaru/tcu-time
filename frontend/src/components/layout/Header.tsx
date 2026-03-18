import { useState } from "react"
import { IconSun, IconMoon, IconLogin } from "@tabler/icons-react"
import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/use-auth"
import { LoginDialog } from "@/components/auth/LoginDialog"
import { ProfileDialog } from "@/components/auth/ProfileDialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
export function Header() {
  const { theme, setTheme } = useTheme()
  const { user } = useAuth()

  const [loginOpen, setLoginOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  const displayName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.email?.split("@")[0] ??
    "ユーザー"

  const avatarUrl = user?.user_metadata?.avatar_url

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
            {theme === "dark" ? <IconMoon /> : <IconSun />}
          </Button>

          {user ? (
            <Button
              variant="ghost"
              className="h-8 w-8 rounded-full p-0"
              onClick={() => setProfileOpen(true)}
            >
              <Avatar className="h-8 w-8 border">
                {avatarUrl && <AvatarImage src={avatarUrl} alt={displayName} />}
                <AvatarFallback className="text-xs">
                  {displayName.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
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
