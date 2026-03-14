import { SidebarTrigger } from "@/components/ui/sidebar"
import { useIsMobile } from "@/hooks/use-mobile"
import { useScroll } from "@/hooks/use-scroll"
import React from "react"

interface PageHeaderProps {
  title: string
  children?: React.ReactNode
}

export function PageHeader({ title, children }: PageHeaderProps) {
  const isMobile = useIsMobile()
  const { headerVisible } = useScroll()

  return (
    <div
      className={`sticky top-14 z-40 flex h-14 items-center border-b bg-background/95 backdrop-blur transition-all duration-300 ease-in-out supports-backdrop-filter:bg-background/75 md:top-0 md:h-16 md:border-b-0 ${
        headerVisible ? "translate-y-0" : "-translate-y-full md:translate-y-0"
      }`}
    >
      <div className="flex w-full items-center gap-3 px-4 md:px-6">
        {!isMobile && (
          <div className="mr-4 flex shrink-0 items-center gap-3">
            <SidebarTrigger className="-ml-1" />
            <h2 className="text-lg font-bold tracking-tight whitespace-nowrap">
              {title}
            </h2>
          </div>
        )}
        <div className="flex min-w-0 flex-1 items-center">{children}</div>
      </div>
    </div>
  )
}
