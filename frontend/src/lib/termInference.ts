export const VALID_TERMS = [
  "前期前",
  "前期後",
  "前期",
  "前集中",
  "後期前",
  "後期後",
  "後期",
  "後集中",
  "通年",
] as const

export type ValidTerm = (typeof VALID_TERMS)[number]

export interface CourseWithTermAndCode {
  code?: string | null
  term?: string | null
  schedules?: Array<{ day?: string | null; period?: number | null }> | null
  day?: string | null
  period?: number | null
}

function hasRegularSchedule(course: CourseWithTermAndCode): boolean {
  if (course.schedules && course.schedules.length > 0) {
    return course.schedules.some(
      (s) =>
        Boolean(s.day) &&
        s.day !== "-" &&
        s.period != null &&
        s.period >= 1 &&
        s.period <= 5
    )
  }
  if (
    course.day &&
    course.day !== "-" &&
    course.period != null &&
    course.period >= 1 &&
    course.period <= 5
  ) {
    return true
  }
  return false
}

export function inferTerm(
  course: CourseWithTermAndCode,
  extractionSemester?: string | null
): ValidTerm {
  const hasSchedule = hasRegularSchedule(course)

  if (course.term && (VALID_TERMS as readonly string[]).includes(course.term)) {
    // If a regular weekly schedule exists, a course is a regular semester course, not an intensive one.
    if (hasSchedule) {
      if (course.term === "前集中") return "前期"
      if (course.term === "後集中") return "後期"
    }
    return course.term as ValidTerm
  }

  const code = (course.code || "").toLowerCase()
  if (code.startsWith("smaa")) return "前期前"
  if (code.startsWith("smab")) return "前期後"
  if (code.startsWith("smaz")) return hasSchedule ? "前期" : "前集中"
  if (code.startsWith("smba")) return "後期前"
  if (code.startsWith("smbb")) return "後期後"
  if (code.startsWith("smbz")) return hasSchedule ? "後期" : "後集中"

  if (code.startsWith("smb") || extractionSemester === "fall") {
    return hasSchedule ? "後期" : "後期前"
  }
  return "前期"
}
