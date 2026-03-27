import { BrowserRouter, Navigate, Outlet, Routes, Route } from "react-router"
import { Layout } from "@/components/layout/Layout"
import { CoursesPage } from "@/pages/CoursesPage"
import { TimetablePage } from "@/pages/TimetablePage"
import { AdminPage } from "@/pages/AdminPage"
import { ReviewPage } from "@/pages/ReviewPage"
import { SettingsProvider } from "@/hooks/use-settings"
import { TutorialProvider } from "@/hooks/use-tutorial"
import { useAuth } from "@/hooks/use-auth"

export function App() {
  return (
    <SettingsProvider>
      <TutorialProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<CoursesPage />} />
            <Route path="timetable" element={<TimetablePage />} />
            <Route element={<AdminRoute />}>
              <Route path="admin" element={<AdminPage />} />
              <Route
                path="admin/review/:extractionId"
                element={<ReviewPage />}
              />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
      </TutorialProvider>
    </SettingsProvider>
  )
}

function AdminRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return null
  }

  if (user?.app_metadata?.role !== "admin") {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}

export default App
