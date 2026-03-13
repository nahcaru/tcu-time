import { BrowserRouter, Routes, Route } from "react-router"
import { Layout } from "@/components/layout/Layout"
import { CoursesPage } from "@/pages/CoursesPage"
import { TimetablePage } from "@/pages/TimetablePage"
import { AdminPage } from "@/pages/AdminPage"

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<CoursesPage />} />
          <Route path="timetable" element={<TimetablePage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
