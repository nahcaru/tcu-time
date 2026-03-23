import { BrowserRouter, Routes, Route } from "react-router"
import { Layout } from "@/components/layout/Layout"
import { CoursesPage } from "@/pages/CoursesPage"
import { TimetablePage } from "@/pages/TimetablePage"
import { AdminPage } from "@/pages/AdminPage"
import { ReviewPage } from "@/pages/ReviewPage"
import { SettingsProvider } from "@/hooks/use-settings"

export function App() {
  return (
    <SettingsProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<CoursesPage />} />
            <Route path="timetable" element={<TimetablePage />} />
            <Route path="admin" element={<AdminPage />} />
            <Route path="admin/review/:extractionId" element={<ReviewPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SettingsProvider>
  )
}

export default App
