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
  IconLogin,
  IconHelp,
  IconDatabase,
  IconExternalLink,
  IconNotebook,
  IconSchool,
  IconDoor,
} from "@tabler/icons-react"
import { useTheme } from "@/components/theme-provider"
import { useAuth } from "@/hooks/use-auth"
import { useTutorial } from "@/hooks/use-tutorial"
import { useDataSources } from "@/hooks/use-data-sources"
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
  const { theme, resolvedTheme, setTheme } = useTheme()
  const { user } = useAuth()
  const { resetAndStartTour } = useTutorial()
  const {
    hasSyllabus,
    hasAdvance,
    hasChangelog,
    timetableUpdatedAt,
    syllabusUpdatedAt,
  } = useDataSources()

  const formatDate = (isoString: string | null) => {
    if (!isoString) return ""
    const d = new Date(isoString)
    return `(${d.getMonth() + 1}/${d.getDate()}取得)`
  }

  // マッピング: pathname → tutorial page key
  const tutorialPageKey =
    location.pathname === "/timetable" ? "timetable" : "courses"

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
        <SidebarHeader className="h-14 items-center justify-center border-b text-xl font-bold">
          <div className="flex items-center gap-2">
            <img
              className="h-8 w-8"
              src={
                resolvedTheme === "dark"
                  ? "/time-icon-dark.png"
                  : "/time-icon.png"
              }
              alt="TCU-TIME"
              width={32}
              height={32}
            />
            {state === "expanded" && "TCU-TIME"}
          </div>
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
                      size="lg"
                      className="group-data-[collapsible=icon]:p-1!"
                    >
                      <Link to={item.url}>
                        <item.icon className="size-6! shrink-0" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
          <SidebarGroup className="mt-auto mb-2">
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild tooltip="教学課 授業時間表へ">
                    <a
                      href="https://www.asc.tcu.ac.jp"
                      target="_blank"
                      rel="noreferrer"
                      className="text-muted-foreground hover:text-sidebar-foreground"
                    >
                      <IconSchool />

                      <span>教学課ウェブサイト</span>
                      <IconExternalLink />
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>

                <SidebarMenuItem>
                  <SidebarMenuButton asChild tooltip="ポータルサイトへ">
                    <a
                      href="https://websrv.tcu.ac.jp/tcu_web_v3/top.do"
                      target="_blank"
                      rel="noreferrer"
                      className="text-muted-foreground hover:text-sidebar-foreground"
                    >
                      <IconDoor />
                      <span>ポータルサイト</span>
                      <IconExternalLink />
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild tooltip="WebClassへ">
                    <a
                      href="https://webclass.tcu.ac.jp/"
                      target="_blank"
                      rel="noreferrer"
                      className="text-muted-foreground hover:text-sidebar-foreground"
                    >
                      <IconNotebook />
                      <span>WebClass</span>
                      <IconExternalLink />
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>

                <SidebarMenuItem className="mt-2">
                  <div className="mx-2 mb-2 border-t border-sidebar-border" />
                  <SidebarMenuButton
                    tooltip="データ取得元と取得日"
                    className="h-auto cursor-default py-2 hover:bg-transparent hover:text-sidebar-foreground"
                  >
                    <IconDatabase className="text-muted-foreground" />
                    <div className="flex flex-col items-start gap-1">
                      <span className="text-xs font-semibold text-muted-foreground">
                        科目データ取得元
                      </span>
                      <div className="mt-1 flex w-full flex-col gap-1.5 text-[10px] leading-tight text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <span className="shrink-0 rounded px-1 text-[10px] font-medium">
                            前期
                          </span>
                          <span>
                            教学課 授業時間表{" "}
                            <span className="ml-1">
                              {formatDate(timetableUpdatedAt)}
                            </span>
                          </span>
                        </div>
                        {hasAdvance && (
                          <p className="pl-7">- 先行履修 反映済み</p>
                        )}
                        {hasChangelog && (
                          <p className="pl-7">- 変更一覧 反映済み</p>
                        )}

                        {hasSyllabus && (
                          <div className="flex items-center gap-1.5">
                            <span className="shrink-0 rounded px-1 text-[10px] font-medium">
                              後期
                            </span>
                            <span>
                              シラバス検索(暫定){" "}
                              <span className="ml-1">
                                {formatDate(syllabusUpdatedAt)}
                              </span>
                            </span>
                          </div>
                        )}

                        <div className="mt-0.5 flex items-center gap-1.5">
                          <span>※単位数はシラバスページより補完</span>
                        </div>
                      </div>
                    </div>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={() => resetAndStartTour(tutorialPageKey)}
                tooltip="使い方"
              >
                <IconHelp />
                <span>使い方</span>
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
