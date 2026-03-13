/** Target department codes from course_targets table */
export const TARGETS = [
  { code: "00", label: "共通" },
  { code: "01", label: "機械専攻(機械工学)" },
  { code: "02", label: "機械専攻(機械システム工学)" },
  { code: "03", label: "電気・化学専攻(電気電子工学)" },
  { code: "04", label: "電気・化学専攻(医用工学)" },
  { code: "05", label: "電気・化学専攻(応用化学)" },
  { code: "06", label: "共同原子力専攻(共同原子力)" },
  { code: "7", label: "建築都市デザイン専攻(建築学)" },
  { code: "08", label: "建築都市デザイン専攻(都市工学)" },
  { code: "09", label: "情報専攻(情報工学)" },
  { code: "10", label: "情報専攻(システム情報工学)" },
  { code: "11", label: "自然科学専攻(自然科学)" },
] as const

export type TargetCode = (typeof TARGETS)[number]["code"]

/** Terms used in schedule data */
export const TERMS = [
  "前期前",
  "前期後",
  "前期",
  "前集中",
  "後期前",
  "後期後",
  "後期",
  "後集中",
] as const

export type Term = (typeof TERMS)[number]

/** Terms grouped by semester for the timetable view */
export const SPRING_TERMS: Term[] = ["前期前", "前期後", "前期", "前集中"]
export const FALL_TERMS: Term[] = ["後期前", "後期後", "後期", "後集中"]

/** Days of the week used in schedule grid */
export const DAYS = ["月", "火", "水", "木", "金", "土"] as const
export type Day = (typeof DAYS)[number]

/** Periods (time slots) */
export const PERIODS = [1, 2, 3, 4, 5] as const

/** Period time ranges */
export const PERIOD_TIMES: Record<number, string> = {
  1: "9:20-11:00",
  2: "11:10-12:50",
  3: "13:40-15:20",
  4: "15:30-17:10",
  5: "17:20-19:00",
}

/**
 * Build a syllabus URL from a course code.
 * Pattern: https://kyoumu.office.tcu.ac.jp/syllabus2/syllabus/index/{code}
 */
export function syllabusUrl(code: string): string {
  return `https://kyoumu.office.tcu.ac.jp/syllabus2/syllabus/index/${code}`
}

/**
 * Checks whether a course's target codes match any of the selected filter codes.
 * Handles the inconsistent 0-padding in the DB (e.g. "0" matches "00", "7" matches "07"/"08").
 */
export function matchesTarget(
  courseTargetCodes: string[],
  selectedCodes: string[]
): boolean {
  if (selectedCodes.length === 0) return true
  const normalize = (c: string) => c.replace(/^0+/, "") || "0"
  const selected = new Set(selectedCodes.map(normalize))
  return courseTargetCodes.some((c) => selected.has(normalize(c)))
}
