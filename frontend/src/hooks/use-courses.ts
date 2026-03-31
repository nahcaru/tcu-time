/**
 * 科目データ取得 hook
 *
 * Fetches course data from Supabase via PostgREST.
 * Supports filtering by target (department), term, and text search.
 */
import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"
import type { CourseWithRelations } from "@/lib/database.types"
import { matchesTarget } from "@/lib/constants"

export interface CourseFilters {
  targets?: string[]
  terms?: string[]
  search?: string
  enrolledOnly?: boolean
  freeSlotsOnly?: boolean
  advanceEnrollmentOnly?: boolean
  enrolledCourseIds?: Set<string>
}

type CoursesCache = {
  data: CourseWithRelations[] | null
  isLoading: boolean
  error: Error | null
  promise: Promise<void> | null
}

const coursesCache: CoursesCache = {
  data: null,
  isLoading: false,
  error: null,
  promise: null,
}

const courseListeners = new Set<() => void>()

function emitCoursesChange() {
  courseListeners.forEach((listener) => listener())
}

function getCoursesSnapshot() {
  return {
    allCourses: coursesCache.data ?? [],
    isLoading: coursesCache.isLoading,
    error: coursesCache.error,
  }
}

async function fetchCoursesOnce() {
  if (coursesCache.promise) return coursesCache.promise
  if (coursesCache.data) return Promise.resolve()

  coursesCache.isLoading = true
  coursesCache.error = null
  emitCoursesChange()

  coursesCache.promise = (async () => {
    const { data: latestCourse, error: latestErr } = await supabase
      .from("courses")
      .select("academic_year")
      .order("academic_year", { ascending: false })
      .limit(1)
      .maybeSingle()

    if (latestErr) {
      coursesCache.error = new Error(latestErr.message)
      coursesCache.isLoading = false
      emitCoursesChange()
      return
    }

    if (!latestCourse) {
      coursesCache.data = []
      coursesCache.isLoading = false
      emitCoursesChange()
      return
    }

    const { data, error: err } = await supabase
      .from("courses")
      .select(
        `
          *,
          schedules (*),
          course_targets (*),
          course_metadata (*)
        `
      )
      .eq("academic_year", latestCourse.academic_year)
      .order("code")

    if (err) {
      coursesCache.error = new Error(err.message)
      coursesCache.isLoading = false
      emitCoursesChange()
      return
    }

    coursesCache.data = (data as CourseWithRelations[]) ?? []
    coursesCache.error = null
    coursesCache.isLoading = false
    emitCoursesChange()
  })().finally(() => {
    coursesCache.promise = null
  })

  return coursesCache.promise
}

// Helper to expand terms into all overlapping terms
function getOverlappingTerms(term: string): string[] {
  if (term === "前期") return ["前期", "前期前", "前期後"]
  if (term === "前期前" || term === "前期後") return [term, "前期"]
  if (term === "後期") return ["後期", "後期前", "後期後"]
  if (term === "後期前" || term === "後期後") return [term, "後期"]
  return [term]
}

export function useCourses(filters?: CourseFilters) {
  const [state, setState] = useState(getCoursesSnapshot)

  useEffect(() => {
    const handleChange = () => {
      setState(getCoursesSnapshot())
    }

    courseListeners.add(handleChange)
    handleChange()
    void fetchCoursesOnce()

    return () => {
      courseListeners.delete(handleChange)
    }
  }, [])

  // Client-side filtering (fast on 183 courses)
  // Let the React Compiler handle memoization — no manual useMemo needed
  let courses = state.allCourses

  // Filter by target codes
  if (filters?.targets && filters.targets.length > 0) {
    courses = courses.filter((c) =>
      matchesTarget(
        c.course_targets.map((t) => t.target_code),
        filters.targets!
      )
    )
  }

  // Filter by terms
  if (filters?.terms && filters.terms.length > 0) {
    const termSet = new Set(filters.terms)
    courses = courses.filter((c) =>
      c.term != null && termSet.has(c.term)
    )
  }

  // Enrolled only filter
  if (filters?.enrolledOnly && filters.enrolledCourseIds) {
    courses = courses.filter((c) => filters.enrolledCourseIds!.has(c.id))
  }

  // Free slots only filter (空きコマ)
  if (filters?.freeSlotsOnly && filters.enrolledCourseIds) {
    const enrolledCourses = state.allCourses.filter((c) =>
      filters.enrolledCourseIds!.has(c.id)
    )
    const occupiedSlots = new Set<string>()
    for (const ec of enrolledCourses) {
      if (!ec.term) continue
      const overlappingTerms = getOverlappingTerms(ec.term)
      for (const s of ec.schedules) {
        for (const t of overlappingTerms) {
          occupiedSlots.add(`${t}-${s.day}-${s.period}`)
        }
      }
    }

    courses = courses.filter((c) => {
      // Hide already enrolled courses
      if (filters.enrolledCourseIds!.has(c.id)) return false
      if (!c.term) return true
      // Keep courses that DO NOT share any slot with occupiedSlots
      return !c.schedules.some((s) =>
        occupiedSlots.has(`${c.term}-${s.day}-${s.period}`)
      )
    })
  }

  // Advance enrollment filter
  if (filters?.advanceEnrollmentOnly) {
    courses = courses.filter((c) => c.advance_enrollment === true)
  }

  // Capture suggestion base (filters applied except text search)
  const suggestionBase = courses

  // Text search (name or instructor)
  if (filters?.search && filters.search.trim()) {
    const q = filters.search.trim().toLowerCase()
    courses = courses.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.instructors.some((i) => i.toLowerCase().includes(q))
    )
  }

  return {
    courses,
    suggestionBase,
    isLoading: state.isLoading,
    error: state.error,
  }
}
