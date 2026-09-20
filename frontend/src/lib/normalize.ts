/**
 * Text normalization utilities for search, display, and database storage.
 */

/**
 * Normalize text for resilient client-side search matching.
 * - Converts fullwidth characters to halfwidth (NFKC).
 * - Replaces fullwidth parentheses （） with halfwidth ().
 * - Replaces fullwidth slash ／ with halfwidth /.
 * - Consolidates consecutive whitespace into a single halfwidth space.
 * - Trims and converts to lower-case.
 */
export function normalizeSearchText(text: string | null | undefined): string {
  if (!text) return ""
  return text
    .normalize("NFKC")
    .replace(/[（]/g, "(")
    .replace(/[）]/g, ")")
    .replace(/[／]/g, "/")
    .replace(/[\s\u3000]+/g, " ")
    .trim()
    .toLowerCase()
}

/**
 * Normalize an instructor's name.
 * - Replaces fullwidth spaces and multiple spaces with a single halfwidth space.
 * - Strips leading/trailing spaces.
 * - Applies NFKC normalization.
 */
export function normalizeInstructorName(
  name: string | null | undefined
): string {
  if (!name) return ""
  return name
    .replace(/[\s\u3000]+/g, " ")
    .normalize("NFKC")
    .trim()
}

/**
 * Normalize course title.
 * - Converts fullwidth alphabets/numbers/slashes to halfwidth.
 * - Converts fullwidth parentheses to halfwidth ().
 * - Fixes missing space after comma in English titles (e.g. "Intelligence,Adv." -> "Intelligence, Adv.").
 * - Consolidates spaces and strips.
 */
export function normalizeCourseName(name: string | null | undefined): string {
  if (!name) return ""
  return name
    .normalize("NFKC")
    .replace(/[（]/g, "(")
    .replace(/[）]/g, ")")
    .replace(/[／]/g, "/")
    .replace(/([A-Za-z0-9]),([A-Za-z0-9])/g, "$1, $2")
    .replace(/[\s\u3000]+/g, " ")
    .trim()
}

/**
 * Normalize classroom name.
 */
export function normalizeRoom(room: string | null | undefined): string {
  if (!room) return ""
  return room
    .normalize("NFKC")
    .replace(/[（]/g, "(")
    .replace(/[）]/g, ")")
    .replace(/[\s\u3000]+/g, " ")
    .trim()
}

/**
 * Normalize target note or general course note.
 * - Converts tildes (～, 〜) to ~.
 * - Converts parentheses to halfwidth ().
 */
export function normalizeNote(note: string | null | undefined): string {
  if (!note) return ""
  return note
    .replace(/[～〜]/g, "~")
    .normalize("NFKC")
    .replace(/[（]/g, "(")
    .replace(/[）]/g, ")")
    .replace(/[\s\u3000]+/g, " ")
    .trim()
}
