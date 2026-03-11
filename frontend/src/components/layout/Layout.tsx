import { Outlet } from "react-router"

export function Layout() {
  return (
    <div className="flex min-h-svh w-full">
      {/* TODO: AppSidebar (desktop) */}
      <div className="flex flex-1 flex-col">
        {/* TODO: Header (mobile) */}
        <main className="flex-1">
          <Outlet />
        </main>
        {/* TODO: BottomNav (mobile) */}
      </div>
    </div>
  )
}
