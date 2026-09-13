import { describe, expect, it, spyOn } from "bun:test"
import {
  saveReviewDraft,
  getSavedReviewIndices,
  type TimetableRawJson,
  type ChangelogRawJson,
  type AdvanceRawJson,
} from "../../lib/approvalService"
import { supabase } from "../../lib/supabase"

describe("getSavedReviewIndices", () => {
  it("returns null when raw is null or undefined", () => {
    expect(getSavedReviewIndices(null)).toBeNull()
    expect(getSavedReviewIndices(undefined)).toBeNull()
  })

  it("returns null when no review state or checked_indices exists", () => {
    const raw: TimetableRawJson = { courses: [] }
    expect(getSavedReviewIndices(raw)).toBeNull()
  })

  it("extracts checked_indices from _review_state", () => {
    const raw: TimetableRawJson = {
      courses: [],
      _review_state: {
        checked_indices: [0, 2, 4],
        saved_at: "2026-09-14T03:00:00Z",
      },
    }
    expect(getSavedReviewIndices(raw)).toEqual([0, 2, 4])
  })

  it("extracts checked_indices from root fallback", () => {
    const raw: ChangelogRawJson = {
      changes: [],
      checked_indices: [1, 3],
    }
    expect(getSavedReviewIndices(raw)).toEqual([1, 3])
  })

  it("prioritizes _review_state.checked_indices over root checked_indices", () => {
    const raw: AdvanceRawJson = {
      names: [],
      _review_state: {
        checked_indices: [5],
        saved_at: "2026-09-14T03:00:00Z",
      },
      checked_indices: [1, 2],
    }
    expect(getSavedReviewIndices(raw)).toEqual([5])
  })
})

describe("saveReviewDraft", () => {
  it("saves draft payload with _review_state and does not update status", async () => {
    let capturedTable = ""
    let capturedUpdate: Record<string, unknown> | null = null
    let capturedEq: { column: string; value: string } | null = null

    const mockFrom = spyOn(supabase, "from").mockImplementation((table: string) => {
      capturedTable = table
      return {
        update: (payload: Record<string, unknown>) => {
          capturedUpdate = payload
          return {
            eq: (col: string, val: string) => {
              capturedEq = { column: col, value: val }
              return Promise.resolve({ error: null })
            },
          }
        },
      } as unknown as ReturnType<typeof supabase.from>
    })

    const sampleRaw: TimetableRawJson = {
      courses: [
        {
          code: "test101",
          name: "情報数学",
          instructors: ["田中"],
        },
      ],
      academic_year: 2026,
    }

    const result = await saveReviewDraft("ext-123", sampleRaw, [0])

    expect(result.ok).toBe(true)
    expect(capturedTable).toBe("extractions")
    expect(capturedEq).toEqual({ column: "id", value: "ext-123" })
    expect(capturedUpdate).toBeDefined()
    expect(capturedUpdate?.status).toBeUndefined() // status is NOT changed to 'approved'
    expect(capturedUpdate?.updated_at).toBeDefined()

    const rawJson = capturedUpdate?.raw_json as TimetableRawJson
    expect(rawJson.courses).toEqual(sampleRaw.courses)
    expect(rawJson._review_state?.checked_indices).toEqual([0])
    expect(typeof rawJson._review_state?.saved_at).toBe("string")

    mockFrom.mockRestore()
  })

  it("returns error when supabase update fails", async () => {
    const mockFrom = spyOn(supabase, "from").mockImplementation(() => {
      return {
        update: () => ({
          eq: () => Promise.resolve({ error: { message: "Database connection error" } }),
        }),
      } as unknown as ReturnType<typeof supabase.from>
    })

    const sampleRaw: TimetableRawJson = { courses: [] }
    const result = await saveReviewDraft("ext-error", sampleRaw, [])

    expect(result.ok).toBe(false)
    expect(result.error).toContain("Database connection error")

    mockFrom.mockRestore()
  })
})

describe("Review draft restoration logic", () => {
  it("restores checkedSet and collapses checked items in expandedSet", () => {
    const itemCount = 5
    const savedIndices = [1, 3]

    const restoredSet = new Set(
      savedIndices.filter((idx) => typeof idx === "number" && idx >= 0 && idx < itemCount)
    )
    const expandedSet = new Set(
      Array.from({ length: itemCount }, (_, i) => i).filter((i) => !restoredSet.has(i))
    )

    expect(restoredSet.size).toBe(2)
    expect(restoredSet.has(1)).toBe(true)
    expect(restoredSet.has(3)).toBe(true)
    expect(restoredSet.has(0)).toBe(false)

    // Items 0, 2, 4 should be expanded; items 1, 3 should be collapsed
    expect(Array.from(expandedSet).sort()).toEqual([0, 2, 4])
  })

  it("filters out invalid or out-of-bounds indices", () => {
    const itemCount = 3
    const savedIndices = [-1, 0, 2, 10]

    const restoredSet = new Set(
      savedIndices.filter((idx) => typeof idx === "number" && idx >= 0 && idx < itemCount)
    )

    expect(Array.from(restoredSet).sort()).toEqual([0, 2])
  })
})
