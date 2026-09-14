import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"

export interface SemesterSource {
  type: "timetable" | "syllabus"
  isTentative: boolean
  updatedAt: string | null
}

export interface DataSourceStatus {
  spring: SemesterSource | null
  fall: SemesterSource | null
  hasChangelog: boolean
  changelogUpdatedAt: string | null
  hasAdvance: boolean
  advanceUpdatedAt: string | null
  isLoading: boolean

  // Backward compatibility fields
  hasTimetable: boolean
  timetableUpdatedAt: string | null
  hasSyllabus: boolean
  syllabusUpdatedAt: string | null
}

export function useDataSources(): DataSourceStatus {
  const [sources, setSources] = useState<DataSourceStatus>({
    spring: null,
    fall: null,
    hasChangelog: false,
    changelogUpdatedAt: null,
    hasAdvance: false,
    advanceUpdatedAt: null,
    isLoading: true,
    hasTimetable: true,
    timetableUpdatedAt: null,
    hasSyllabus: false,
    syllabusUpdatedAt: null,
  })

  useEffect(() => {
    let cancelled = false

    async function fetchSources() {
      // 1. Identify latest academic year from courses or extractions
      const { data: latestCourse } = await supabase
        .from("courses")
        .select("academic_year")
        .order("academic_year", { ascending: false })
        .limit(1)
        .maybeSingle()

      let targetYear: number | null | undefined = latestCourse?.academic_year
      if (targetYear == null) {
        const { data: latestExt } = await supabase
          .from("extractions")
          .select("academic_year")
          .order("academic_year", { ascending: false })
          .limit(1)
          .maybeSingle()
        targetYear = latestExt?.academic_year
      }

      if (cancelled) return
      if (targetYear == null) {
        setSources((s) => ({ ...s, isLoading: false }))
        return
      }

      // 2. Fetch approved extractions for targetYear
      const { data: extractionsData } = await supabase
        .from("extractions")
        .select(
          "id, pdf_type, semester, is_tentative, academic_year, status, created_at, updated_at"
        )
        .eq("academic_year", targetYear)
        .eq("status", "approved")
        .order("created_at", { ascending: false })

      if (cancelled) return

      // 3. Fetch courses summary for targetYear
      const { data: coursesData } = await supabase
        .from("courses")
        .select("source_type, term, is_tentative, advance_enrollment, updated_at")
        .eq("academic_year", targetYear)

      if (cancelled) return

      const courses: CourseSummary[] = coursesData ?? []
      const extractions: ExtractionSummary[] = extractionsData ?? []

      const resolved = resolveDataSources(extractions, courses)

      setSources({
        ...resolved,
        isLoading: false,
      })
    }

    fetchSources()

    return () => {
      cancelled = true
    }
  }, [])

  return sources
}

export interface CourseSummary {
  source_type?: string | null
  term?: string | null
  semester?: string | null
  is_tentative?: boolean | null
  advance_enrollment?: boolean | null
  updated_at?: string | null
}

export interface ExtractionSummary {
  id?: string
  pdf_type?: string | null
  semester?: string | null
  is_tentative?: boolean | null
  academic_year?: number | null
  status?: string | null
  created_at?: string | null
  updated_at?: string | null
}

function isSpringCourse(c: CourseSummary): boolean {
  if (c.semester === "spring") return true
  if (c.term && (c.term.startsWith("前") || c.term === "前期")) return true
  return false
}

function isFallCourse(c: CourseSummary): boolean {
  if (c.semester === "fall") return true
  if (c.term && (c.term.startsWith("後") || c.term === "後期")) return true
  return false
}

export function resolveDataSources(
  extractions: ExtractionSummary[],
  courses: CourseSummary[]
): Omit<DataSourceStatus, "isLoading"> {
  // --- Changelogs ---
  const approvedChangelogs = extractions.filter(
    (e) => e.pdf_type === "changelog" && (e.status === "approved" || !e.status)
  )
  const hasChangelog =
    approvedChangelogs.length > 0 ||
    courses.some((c) => c.source_type === "changelog")
  const changelogUpdatedAt =
    approvedChangelogs[0]?.updated_at ??
    approvedChangelogs[0]?.created_at ??
    null

  // --- Advance Enrollment ---
  const approvedAdvance = extractions.filter(
    (e) => e.pdf_type === "advance_enrollment" && (e.status === "approved" || !e.status)
  )
  const hasAdvance =
    approvedAdvance.length > 0 ||
    courses.some((c) => c.advance_enrollment === true)
  const advanceUpdatedAt =
    approvedAdvance[0]?.updated_at ??
    approvedAdvance[0]?.created_at ??
    null

  // --- Spring Source ---
  const springTimetableExt = extractions.find(
    (e) =>
      e.pdf_type === "timetable" &&
      (e.status === "approved" || !e.status) &&
      (e.semester === "spring" || e.semester === null)
  )
  const springCourses = courses.filter(isSpringCourse)
  const hasSpring = !!springTimetableExt || springCourses.length > 0
  let springSource: SemesterSource | null = null

  if (hasSpring) {
    const isTentative =
      springTimetableExt?.is_tentative ??
      springCourses.some((c) => c.is_tentative)
    const maxSpringUpdate = springCourses.reduce<string | null>((max, c) => {
      if (!c.updated_at) return max
      if (!max || c.updated_at > max) return c.updated_at
      return max
    }, null)
    springSource = {
      type: "timetable",
      isTentative: Boolean(isTentative),
      updatedAt:
        springTimetableExt?.updated_at ??
        springTimetableExt?.created_at ??
        maxSpringUpdate ??
        null,
    }
  }

  // --- Fall Source ---
  const fallCourses = courses.filter(isFallCourse)
  const fallTimetableExt = extractions.find(
    (e) =>
      e.pdf_type === "timetable" &&
      (e.status === "approved" || !e.status) &&
      (e.semester === "fall" || e.semester === null)
  )
  const fallTimetableCourses = fallCourses.filter(
    (c) => c.source_type === "timetable"
  )
  const fallSyllabusCourses = fallCourses.filter(
    (c) => c.source_type === "syllabus"
  )

  let fallSource: SemesterSource | null = null
  if (fallTimetableExt || fallTimetableCourses.length > 0) {
    const isTentative =
      fallTimetableExt?.is_tentative ??
      fallTimetableCourses.some((c) => c.is_tentative)
    const maxFallUpdate = fallTimetableCourses.reduce<string | null>((max, c) => {
      if (!c.updated_at) return max
      if (!max || c.updated_at > max) return c.updated_at
      return max
    }, null)
    fallSource = {
      type: "timetable",
      isTentative: Boolean(isTentative),
      updatedAt:
        fallTimetableExt?.updated_at ??
        fallTimetableExt?.created_at ??
        maxFallUpdate ??
        null,
    }
  } else if (fallSyllabusCourses.length > 0) {
    const maxSyllabusUpdate = fallSyllabusCourses.reduce<string | null>((max, c) => {
      if (!c.updated_at) return max
      if (!max || c.updated_at > max) return c.updated_at
      return max
    }, null)
    fallSource = {
      type: "syllabus",
      isTentative: true,
      updatedAt: maxSyllabusUpdate ?? null,
    }
  }

  // Backward compatibility fields
  const hasTimetable = !!springSource || fallSource?.type === "timetable"
  const timetableUpdatedAt =
    springSource?.updatedAt ?? fallSource?.updatedAt ?? null
  const hasSyllabus = fallSource?.type === "syllabus"
  const syllabusUpdatedAt = hasSyllabus ? fallSource?.updatedAt ?? null : null

  return {
    spring: springSource,
    fall: fallSource,
    hasChangelog,
    changelogUpdatedAt,
    hasAdvance,
    advanceUpdatedAt,
    hasTimetable,
    timetableUpdatedAt,
    hasSyllabus,
    syllabusUpdatedAt,
  }
}
