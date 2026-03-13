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

// Helper to expand terms into all overlapping terms
function getOverlappingTerms(term: string): string[] {
  if (term === "前期") return ["前期", "前期前", "前期後"]
  if (term === "前期前" || term === "前期後") return [term, "前期"]
  if (term === "後期") return ["後期", "後期前", "後期後"]
  if (term === "後期前" || term === "後期後") return [term, "後期"]
  return [term]
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

  // Free slots only filter (空きコマ)
  if (filters?.freeSlotsOnly && filters.enrolledCourseIds) {
    const enrolledCourses = allCourses.filter(c => filters.enrolledCourseIds!.has(c.id))
    const occupiedSlots = new Set<string>()
    for (const ec of enrolledCourses) {
      for (const s of ec.schedules) {
        const overlappingTerms = getOverlappingTerms(s.term)
        for (const t of overlappingTerms) {
          occupiedSlots.add(`${t}-${s.day}-${s.period}`)
        }
      }
    }
    
    courses = courses.filter((c) => {
      // Hide already enrolled courses
      if (filters.enrolledCourseIds!.has(c.id)) return false
      // Keep courses that DO NOT share any slot with occupiedSlots
      return !c.schedules.some((s) => occupiedSlots.has(`${s.term}-${s.day}-${s.period}`))
    })
  }

  // Advance enrollment filter
  if (filters?.advanceEnrollmentOnly) {
    courses = courses.filter((c) => c.advance_enrollment === true)
  }

  return { courses, isLoading, error }
}
