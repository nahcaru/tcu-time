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
  enrolledCourseIds?: Set<string>
}

export function useCourses(filters?: CourseFilters) {
  const [allCourses, setAllCourses] = useState<CourseWithRelations[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // Fetch all courses once (183 courses — small enough to fetch in one go)
  useEffect(() => {
    let cancelled = false

    async function fetchCourses() {
      setIsLoading(true)
      setError(null)

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
        .order("code")

      if (cancelled) return

      if (err) {
        setError(new Error(err.message))
        setIsLoading(false)
        return
      }

      setAllCourses((data as CourseWithRelations[]) ?? [])
      setIsLoading(false)
    }

    fetchCourses()
    return () => {
      cancelled = true
    }
  }, [])

  // Client-side filtering (fast on 183 courses)
  // Let the React Compiler handle memoization — no manual useMemo needed
  let courses = allCourses

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
      c.schedules.some((s) => termSet.has(s.term))
    )
  }

  // Text search (name or instructor)
  if (filters?.search && filters.search.trim()) {
    const q = filters.search.trim().toLowerCase()
    courses = courses.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.instructors.some((i) => i.toLowerCase().includes(q))
    )
  }

  // Enrolled only filter
  if (filters?.enrolledOnly && filters.enrolledCourseIds) {
    courses = courses.filter((c) => filters.enrolledCourseIds!.has(c.id))
  }

  return { courses, isLoading, error }
}
