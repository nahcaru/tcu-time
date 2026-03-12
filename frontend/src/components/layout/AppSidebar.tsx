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
  IconUser,
} from "@tabler/icons-react"
import { useTheme } from "@/components/theme-provider"

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

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="flex h-14 items-center justify-center border-b text-xl font-bold">
        {state === "collapsed" ? "TiME" : "TCU-TIME"}
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
            <SidebarMenuButton 
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")} 
              tooltip="テーマ切替"
            >
              {theme === "dark" ? <IconMoon /> : <IconSun />}
              <span>テーマ切替</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="プロフィール">
              <Link to="/profile">
                <IconUser />
                <span>プロフィール</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="情報">
              <IconInfoCircle />
              <span>情報</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
