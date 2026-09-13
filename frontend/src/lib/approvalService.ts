/**
 * approvalService.ts
 *
 * フロントエンドから直接 Supabase クライアントを使って
 * extractions の承認ロジックを実行するサービス。
 */

import { supabase } from "@/lib/supabase"
import type { Database, Json } from "@/lib/database.types"

// ---------------------------------------------------------------------------
// Constants (shared with ReviewPage editors)
// ---------------------------------------------------------------------------

import { inferTerm, VALID_TERMS, type ValidTerm } from "./termInference"

export const VALID_DAYS = ["月", "火", "水", "木", "金", "土"] as const
export { VALID_TERMS, type ValidTerm, inferTerm }
export const VALID_PERIODS = [1, 2, 3, 4, 5] as const
export const CHANGE_TYPES = ["create", "update", "delete"] as const

// ---------------------------------------------------------------------------
// Payload types
// ---------------------------------------------------------------------------

export interface RawSchedule {
  day: string
  period: number
}

export interface RawTarget {
  target_code: string
  target_name: string
  note?: string
}

export interface RawCourse {
  code: string
  name: string
  instructors: string[]
  year_level?: number
  class_section?: string
  term?: string
  room?: string
  notes?: string
  schedules?: RawSchedule[]
  targets?: RawTarget[]
}

export interface RawFieldChange {
  field: string
  old_value?: string | null
  new_value?: string | null
}

export function parseScheduleString(
  text: string | null | undefined
): RawSchedule[] {
  if (!text) return []
  const schedules: RawSchedule[] = []
  const matches = text.matchAll(/([月火水木金土])\s*([1-5])/g)
  for (const m of matches) {
    schedules.push({
      day: m[1],
      period: Number(m[2]),
    })
  }
  return schedules
}

export interface RawChange {
  change_type: "create" | "update" | "delete"
  course_code?: string | null
  course_name?: string
  term?: string | null
  day?: string | null
  period?: number | string | null
  schedules?: RawSchedule[]
  instructors?: string[]
  room?: string | null
  targets?: RawTarget[]
  changes?: RawFieldChange[]
}

export interface ReviewState {
  checked_indices: number[]
  saved_at: string
}

export interface BaseRawJson {
  _review_state?: ReviewState
  checked_indices?: number[]
}

export interface TimetableRawJson extends BaseRawJson {
  courses: RawCourse[]
  semester?: string
  is_tentative?: boolean
  academic_year?: number
  count?: number
}

export interface ChangelogRawJson extends BaseRawJson {
  changes: RawChange[]
  semester?: string
  academic_year?: number
  count?: number
}

export interface AdvanceRawJson extends BaseRawJson {
  names: string[]
  academic_year?: number
  count?: number
}

export type ExtractionRawJson =
  | TimetableRawJson
  | ChangelogRawJson
  | AdvanceRawJson

export function getSavedReviewIndices(
  raw: ExtractionRawJson | null | undefined
): number[] | null {
  if (!raw) return null
  if (Array.isArray(raw._review_state?.checked_indices)) {
    return raw._review_state.checked_indices
  }
  if (Array.isArray(raw.checked_indices)) {
    return raw.checked_indices
  }
  return null
}

// ---------------------------------------------------------------------------
// Timetable approval
// ---------------------------------------------------------------------------

async function applyTimetableApproval(
  extractionId: string,
  raw: TimetableRawJson
): Promise<number> {
  const { courses = [], academic_year, is_tentative = false, semester } = raw

  if (semester === "fall" && !is_tentative && academic_year) {
    await supabase
      .from("courses")
      .delete()
      .eq("academic_year", academic_year)
      .eq("is_tentative", true)
  }

  let count = 0

  for (const course of courses) {
    const { data: courseRow, error: courseErr } = await supabase
      .from("courses")
      .upsert(
        {
          code: course.code,
          name: course.name,
          instructors: course.instructors,
          year_level: course.year_level ?? 1,
          class_section: course.class_section ?? "",
          notes: course.notes ?? "",
          academic_year: academic_year ?? new Date().getFullYear(),
          is_tentative,
          extraction_id: extractionId,
          status: "active",
          source_type: "timetable",
          term: course.term || inferTerm(course, semester),
          room: course.room,
        },
        { onConflict: "code,academic_year" }
      )
      .select("id")
      .single()

    if (courseErr || !courseRow) {
      console.error("course upsert failed:", courseErr, course.code)
      continue
    }

    const courseId = courseRow.id

    // Replace schedules — term and room come from course level
    await supabase.from("schedules").delete().eq("course_id", courseId)
    if (course.schedules && course.schedules.length > 0) {
      await supabase.from("schedules").insert(
        course.schedules.map((s) => ({
          course_id: courseId,
          day: s.day,
          period: s.period,
        }))
      )
    }

    // Replace targets
    await supabase.from("course_targets").delete().eq("course_id", courseId)
    if (course.targets && course.targets.length > 0) {
      await supabase.from("course_targets").insert(
        course.targets.map((t) => ({
          course_id: courseId,
          target_code: t.target_code,
          target_name: t.target_name,
          note: t.note ?? "",
        }))
      )
    }

    count++
  }

  return count
}

// ---------------------------------------------------------------------------
// Changelog approval
// ---------------------------------------------------------------------------

async function applyChangelogApproval(
  extractionId: string,
  raw: ChangelogRawJson
): Promise<number> {
  const { changes = [], academic_year } = raw
  let count = 0

  for (const change of changes) {
    if (change.change_type === "create") {
      if (!change.course_name) continue

      const instructors =
        change.instructors && change.instructors.length > 0
          ? change.instructors
          : ["未定"]

      const { data: courseRow, error: courseErr } = await supabase
        .from("courses")
        .upsert(
          {
            code: change.course_code ?? "",
            name: change.course_name,
            instructors,
            room: change.room ?? null,
            term: change.term ?? null,
            academic_year: academic_year ?? new Date().getFullYear(),
            status: "active",
            source_type: "changelog",
            extraction_id: extractionId,
          },
          { onConflict: "code,academic_year" }
        )
        .select("id")
        .single()

      if (courseRow && !courseErr) {
        const courseId = courseRow.id
        const schedules =
          change.schedules && change.schedules.length > 0
            ? change.schedules
            : parseScheduleString(
                [change.day, change.period ? `${change.period}限` : ""]
                  .filter(Boolean)
                  .join(" ")
              )

        if (schedules.length > 0) {
          await supabase.from("schedules").delete().eq("course_id", courseId)
          await supabase.from("schedules").insert(
            schedules.map((s) => ({
              course_id: courseId,
              day: s.day,
              period: s.period,
            }))
          )
        }

        if (change.targets && change.targets.length > 0) {
          await supabase.from("course_targets").delete().eq("course_id", courseId)
          await supabase.from("course_targets").insert(
            change.targets.map((t) => ({
              course_id: courseId,
              target_code: t.target_code,
              target_name: t.target_name,
              note: t.note ?? "",
            }))
          )
        }
      }
      count++
    } else if (
      change.change_type === "update" ||
      change.change_type === "delete"
    ) {
      let query = supabase.from("courses").select("id").eq("status", "active")
      if (academic_year) query = query.eq("academic_year", academic_year)
      if (change.course_code) {
        query = query.eq("code", change.course_code)
      } else if (change.course_name) {
        query = query.ilike("name", change.course_name)
      } else {
        continue
      }

      const { data: found } = await query.limit(1).single()
      if (!found) continue

      if (change.change_type === "delete") {
        await supabase
          .from("courses")
          .update({ status: "cancelled" })
          .eq("id", found.id)
      } else {
        const updates: Record<string, unknown> = {}
        const fieldMap: Record<string, string> = {
          "教室": "room",
          "担当者": "instructors",
          "科目名": "name",
          "備考": "notes",
          "学期": "term",
          "開講期": "term",
          "講義コード": "code",
        }
        for (const fc of change.changes ?? []) {
          const field = fc.field.trim()
          if (field === "曜日時限" || field === "時限" || field === "曜日") {
            const newScheds = parseScheduleString(fc.new_value)
            if (newScheds.length > 0) {
              await supabase.from("schedules").delete().eq("course_id", found.id)
              await supabase.from("schedules").insert(
                newScheds.map((s) => ({
                  course_id: found.id,
                  day: s.day,
                  period: s.period,
                }))
              )
            }
          } else if (field === "受講対象") {
            if (fc.new_value) {
              const targetList = fc.new_value
                .split(/[,、/]/)
                .map((s) => s.trim())
                .filter(Boolean)
              if (targetList.length > 0) {
                await supabase
                  .from("course_targets")
                  .delete()
                  .eq("course_id", found.id)
                await supabase.from("course_targets").insert(
                  targetList.map((t) => ({
                    course_id: found.id,
                    target_code: "",
                    target_name: t,
                    note: "",
                  }))
                )
              }
            }
          } else {
            const key = fieldMap[field] ?? field
            if (key === "instructors") {
              updates[key] = fc.new_value
                ? fc.new_value.split(/[,、]/).map((s) => s.trim()).filter(Boolean)
                : ["未定"]
            } else {
              updates[key] = fc.new_value
            }
          }
        }
        if (Object.keys(updates).length > 0) {
          await supabase
            .from("courses")
            .update(updates as Database["public"]["Tables"]["courses"]["Update"])
            .eq("id", found.id)
        }
      }
      count++
    }
  }

  return count
}

// ---------------------------------------------------------------------------
// Advance enrollment approval
// ---------------------------------------------------------------------------

async function applyAdvanceApproval(
  _extractionId: string,
  raw: AdvanceRawJson
): Promise<number> {
  const { names = [], academic_year } = raw
  const year = academic_year ?? new Date().getFullYear()

  await supabase
    .from("courses")
    .update({ advance_enrollment: false })
    .eq("academic_year", year)
    .eq("advance_enrollment", true)

  let count = 0
  for (const name of names) {
    const { data: found } = await supabase
      .from("courses")
      .select("id")
      .eq("academic_year", year)
      .eq("status", "active")
      .ilike("name", name)
      .limit(1)
      .single()

    if (found) {
      await supabase
        .from("courses")
        .update({ advance_enrollment: true })
        .eq("id", found.id)
      count++
    }
  }

  return count
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function approveExtraction(
  extractionId: string,
  pdfType: string,
  editedRawJson: ExtractionRawJson
): Promise<{ ok: boolean; count: number; error?: string }> {
  try {
    const { error: saveErr } = await supabase
      .from("extractions")
      .update({
        raw_json: editedRawJson as unknown as Json,
        updated_at: new Date().toISOString(),
      })
      .eq("id", extractionId)

    if (saveErr) throw new Error(saveErr.message)

    let count = 0
    if (pdfType === "timetable") {
      count = await applyTimetableApproval(
        extractionId,
        editedRawJson as TimetableRawJson
      )
    } else if (pdfType === "changelog") {
      count = await applyChangelogApproval(
        extractionId,
        editedRawJson as ChangelogRawJson
      )
    } else if (pdfType === "advance_enrollment") {
      count = await applyAdvanceApproval(
        extractionId,
        editedRawJson as AdvanceRawJson
      )
    }

    const { error: statusErr } = await supabase
      .from("extractions")
      .update({ status: "approved", updated_at: new Date().toISOString() })
      .eq("id", extractionId)

    if (statusErr) throw new Error(statusErr.message)

    return { ok: true, count }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, count: 0, error: message }
  }
}

// ---------------------------------------------------------------------------
// Review draft saving
// ---------------------------------------------------------------------------

export async function saveReviewDraft(
  extractionId: string,
  editedJson: ExtractionRawJson,
  checkedIndices: number[]
): Promise<{ ok: boolean; error?: string }> {
  try {
    const payload: ExtractionRawJson = {
      ...editedJson,
      _review_state: {
        checked_indices: checkedIndices,
        saved_at: new Date().toISOString(),
      },
    }

    const { error: saveErr } = await supabase
      .from("extractions")
      .update({
        raw_json: payload as unknown as Json,
        updated_at: new Date().toISOString(),
      })
      .eq("id", extractionId)

    if (saveErr) throw new Error(saveErr.message)

    return { ok: true }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: message }
  }
}
