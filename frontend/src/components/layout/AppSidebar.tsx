import { useState } from "react"
import { Link, useLocation } from "react-router"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import {
  IconList,
  IconTableFilled,
  IconSun,
  IconMoon,
  IconInfoCircle,
  IconLogin,
} from "@tabler/icons-react"
import { useTheme } from "@/components/theme-provider"
import { useAuth } from "@/hooks/use-auth"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { LoginDialog } from "@/components/auth/LoginDialog"
import { ProfileDialog } from "@/components/auth/ProfileDialog"

const navItems = [
  {
    title: "科目一覧",
    url: "/",
    icon: IconList,
  },
  {
    title: "時間割",
    url: "/timetable",
    icon: IconTableFilled,
  },
]

export function AppSidebar() {
  const { state } = useSidebar()
  const location = useLocation()
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
      <Sidebar collapsible="icon" variant="inset" className="dark">
        <SidebarHeader className="flex h-14 items-center justify-center border-b text-xl font-bold text-sidebar-primary">
          {state === "collapsed" ? "TIME" : "TCU-TIME"}
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={location.pathname === item.url}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton tooltip="情報">
                <IconInfoCircle />
                <span>情報</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                tooltip="テーマ切替"
              >
                {theme === "dark" ? <IconMoon /> : <IconSun />}
                <span>テーマ切替</span>
              </SidebarMenuButton>
            </SidebarMenuItem>

            <SidebarMenuItem>
              {user ? (
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                  onClick={() => setProfileOpen(true)}
                  tooltip="プロフィール"
                >
                  <Avatar className="h-8 w-8 rounded-lg">
                    {avatarUrl && (
                      <AvatarImage src={avatarUrl} alt={displayName} />
                    )}
                    <AvatarFallback className="rounded-lg">
                      {displayName.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">
                      {displayName}
                    </span>
                    <span className="truncate text-xs">{user.email}</span>
                  </div>
                </SidebarMenuButton>
              ) : (
                <SidebarMenuButton
                  tooltip="ログイン"
                  onClick={() => setLoginOpen(true)}
                >
                  <IconLogin />
                  <span>ログイン</span>
                </SidebarMenuButton>
              )}
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>

      <LoginDialog open={loginOpen} onOpenChange={setLoginOpen} />
      <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />
    </>
  )
}
