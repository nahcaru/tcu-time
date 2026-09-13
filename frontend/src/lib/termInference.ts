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
}

export function inferTerm(course: CourseWithTermAndCode, extractionSemester?: string | null): ValidTerm {
  if (course.term && (VALID_TERMS as readonly string[]).includes(course.term)) {
    return course.term as ValidTerm
  }
  const code = (course.code || "").toLowerCase()
  if (code.startsWith("smaa")) return "前期前"
  if (code.startsWith("smab")) return "前期後"
  if (code.startsWith("smaz")) return "前集中"
  if (code.startsWith("smba")) return "後期前"
  if (code.startsWith("smbb")) return "後期後"
  if (code.startsWith("smbz")) return "後集中"
  if (code.startsWith("smb") || extractionSemester === "fall") return "後期前"
  return "前期"
}
