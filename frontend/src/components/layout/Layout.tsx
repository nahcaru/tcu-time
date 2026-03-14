import { useEffect } from "react"
import { Outlet, useLocation } from "react-router"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppSidebar } from "./AppSidebar"
import { BottomNav } from "./BottomNav"
import { Header } from "./Header"
import { ScrollProvider, useScroll } from "@/hooks/use-scroll"

export function Layout() {
  return (
    <SidebarProvider defaultOpen>
      <TooltipProvider>
        <AppSidebar />
        <SidebarInset className="overflow-hidden h-screen flex flex-col">
          <ScrollProvider>
            <Header />
            <MainContent />
            <BottomNav />
          </ScrollProvider>
        </SidebarInset>
      </TooltipProvider>
    </SidebarProvider>
  )
}

function MainContent() {
  const { scrollRootRef } = useScroll()
  const location = useLocation()

  useEffect(() => {
    if (scrollRootRef.current) {
      scrollRootRef.current.scrollTop = 0
    }
  }, [location.pathname, scrollRootRef])

  return (
    <main 
      ref={scrollRootRef}
      className="flex-1 overflow-auto pb-20 md:pb-0"
    >
      <Outlet />
    </main>
  )
}
