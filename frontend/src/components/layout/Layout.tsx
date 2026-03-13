import { Outlet } from "react-router"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppSidebar } from "./AppSidebar"
import { BottomNav } from "./BottomNav"
import { Header } from "./Header"

export function Layout() {
  return (
    <SidebarProvider defaultOpen>
      <TooltipProvider>
        <AppSidebar />
        <SidebarInset>
          <div className="flex flex-1 flex-col overflow-hidden">
            <Header />
            <main className="flex-1 overflow-auto p-4 pb-20 md:p-6 md:pb-6">
              <Outlet />
            </main>
            <BottomNav />
          </div>
        </SidebarInset>
      </TooltipProvider>
    </SidebarProvider>
  )
}
