/** 時限情報 */
export const TIME_SLOTS = [
  { period: 1, start: "9:20", end: "11:00" },
  { period: 2, start: "11:10", end: "12:50" },
  { period: 3, start: "13:40", end: "15:20" },
  { period: 4, start: "15:30", end: "17:10" },
  { period: 5, start: "17:20", end: "19:00" },
] as const

/** 曜日 */
export const WEEKDAYS = ["月", "火", "水", "木", "金", "土"] as const

/** 学期 */
export const TERMS = [
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

/** 専攻一覧 (カリキュラムコードスクレイピング後に確定) */
export const MAJORS = [
  { label: "共通", value: "00" },
  { label: "機械(1)", value: "01" },
  { label: "機械(2)", value: "02" },
  { label: "機械システム", value: "03" },
  { label: "エネルギー化学", value: "04" },
  { label: "電気・化学", value: "05" },
  { label: "共同原子力", value: "06" },
  { label: "建築都市デザイン(1)", value: "07" },
  { label: "建築都市デザイン(2)", value: "08" },
  { label: "情報", value: "09" },
  { label: "自然", value: "11" },
] as const

/** 必選区分 */
export const COMPULSORINESS = ["必修", "選択必修", "選択"] as const
