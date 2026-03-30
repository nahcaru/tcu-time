import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"

interface DataSourceStatus {
  hasTimetable: boolean;
  timetableUpdatedAt: string | null;
  hasSyllabus: boolean;
  syllabusUpdatedAt: string | null;
  hasChangelog: boolean;
  hasAdvance: boolean;
  isLoading: boolean;
}

export function useDataSources() {
  const [sources, setSources] = useState<DataSourceStatus>({
    hasTimetable: true, // Default baseline
    timetableUpdatedAt: null,
    hasSyllabus: false,
    syllabusUpdatedAt: null,
    hasChangelog: false,
    hasAdvance: false,
    isLoading: true,
  })

  useEffect(() => {
    let cancelled = false;

    async function fetchSources() {
      const { data: latest } = await supabase
        .from("courses")
        .select("academic_year")
        .order("academic_year", { ascending: false })
        .limit(1)
        .maybeSingle()

      if (cancelled) return;
      if (!latest) {
        setSources((s) => ({ ...s, isLoading: false }))
        return
      }

      const { data } = await supabase
        .from("courses")
        .select("source_type, advance_enrollment, updated_at")
        .eq("academic_year", latest.academic_year)

      if (cancelled) return;
      if (!data) {
        setSources((s) => ({ ...s, isLoading: false }))
        return
      }

      // Find max updated_at for timetable
      const timetableItems = data.filter(d => d.source_type === "timetable")
      const maxTimetableUpdate = timetableItems.length > 0 
        ? timetableItems.reduce((max, item) => 
            !max || (item.updated_at && item.updated_at > max) ? item.updated_at : max
          , null as string | null) 
        : null

      // Find max updated_at for syllabus
      const syllabusItems = data.filter(d => d.source_type === "syllabus")
      const maxSyllabusUpdate = syllabusItems.length > 0
        ? syllabusItems.reduce((max, item) =>
            !max || (item.updated_at && item.updated_at > max) ? item.updated_at : max
          , null as string | null)
        : null

      setSources({
        hasTimetable: timetableItems.length > 0,
        timetableUpdatedAt: maxTimetableUpdate,
        hasSyllabus: syllabusItems.length > 0,
        syllabusUpdatedAt: maxSyllabusUpdate,
        hasChangelog: data.some((d) => d.source_type === "changelog"),
        hasAdvance: data.some((d) => d.advance_enrollment === true),
        isLoading: false,
      })
    }
    fetchSources()

    return () => {
      cancelled = true;
    }
  }, [])

  return sources
}
