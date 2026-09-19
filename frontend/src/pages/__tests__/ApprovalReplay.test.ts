import { describe, expect, it, spyOn } from "bun:test"
import {
  approveExtraction,
  replayApprovedChangelogs,
  replayApprovedAdvanceEnrollment,
  type TimetableRawJson,
} from "../../lib/approvalService"
import { supabase } from "../../lib/supabase"

describe("replayApprovedChangelogs", () => {
  it("returns 0 when no approved changelogs exist for the year", async () => {
    const mockFrom = spyOn(supabase, "from").mockImplementation((table: string) => {
      if (table === "extractions") {
        return {
          select: () => ({
            eq: () => ({
              eq: () => ({
                eq: () => ({
                  order: () => Promise.resolve({ data: [], error: null }),
                  or: () => ({
                    order: () => Promise.resolve({ data: [], error: null }),
                  }),
                }),
              }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }
      return {} as unknown as ReturnType<typeof supabase.from>
    })

    const result = await replayApprovedChangelogs(2026, "spring")
    expect(result).toEqual({ extractionCount: 0, changeCount: 0 })

    mockFrom.mockRestore()
  })

  it("queries approved changelogs in chronological order and applies changes", async () => {
    let queriedType = ""
    let queriedStatus = ""
    let queriedYear = 0

    const mockFrom = spyOn(supabase, "from").mockImplementation((table: string) => {
      if (table === "extractions") {
        return {
          select: () => ({
            eq: (col1: string, val1: string) => ({
              eq: (col2: string, val2: string) => ({
                eq: (col3: string, val3: number) => {
                  if (col1 === "pdf_type") queriedType = val1
                  if (col2 === "status") queriedStatus = val2
                  if (col3 === "academic_year") queriedYear = val3
                  return {
                    order: () =>
                      Promise.resolve({
                        data: [
                          {
                            id: "ch-1",
                            academic_year: 2026,
                            semester: "spring",
                            created_at: "2026-04-01T00:00:00Z",
                            raw_json: {
                              academic_year: 2026,
                              changes: [
                                {
                                  change_type: "create",
                                  course_code: "new101",
                                  course_name: "新設講義",
                                  instructors: ["佐藤"],
                                },
                              ],
                            },
                          },
                        ],
                        error: null,
                      }),
                  }
                },
              }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      if (table === "courses") {
        return {
          upsert: () => ({
            select: () => ({
              single: () => Promise.resolve({ data: { id: "course-new101" }, error: null }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      return {} as unknown as ReturnType<typeof supabase.from>
    })

    const result = await replayApprovedChangelogs(2026)
    expect(queriedType).toBe("changelog")
    expect(queriedStatus).toBe("approved")
    expect(queriedYear).toBe(2026)
    expect(result.extractionCount).toBe(1)
    expect(result.changeCount).toBe(1)

    mockFrom.mockRestore()
  })
})

describe("replayApprovedAdvanceEnrollment", () => {
  it("returns 0 when no approved advance enrollment exists for the year", async () => {
    const mockFrom = spyOn(supabase, "from").mockImplementation((table: string) => {
      if (table === "extractions") {
        return {
          select: () => ({
            eq: () => ({
              eq: () => ({
                eq: () => ({
                  order: () => Promise.resolve({ data: [], error: null }),
                }),
              }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }
      return {} as unknown as ReturnType<typeof supabase.from>
    })

    const result = await replayApprovedAdvanceEnrollment(2026)
    expect(result).toEqual({ extractionCount: 0, courseCount: 0 })

    mockFrom.mockRestore()
  })

  it("finds approved advance enrollment and applies advance_enrollment flag to matching courses", async () => {
    let queriedType = ""
    let queriedStatus = ""
    let queriedYear = 0
    let resetDone = false
    const updatedIds: string[] = []

    const mockFrom = spyOn(supabase, "from").mockImplementation((table: string) => {
      if (table === "extractions") {
        return {
          select: () => ({
            eq: (col1: string, val1: string) => ({
              eq: (col2: string, val2: string) => ({
                eq: (col3: string, val3: number) => {
                  if (col1 === "pdf_type") queriedType = val1
                  if (col2 === "status") queriedStatus = val2
                  if (col3 === "academic_year") queriedYear = val3
                  return {
                    order: () =>
                      Promise.resolve({
                        data: [
                          {
                            id: "adv-1",
                            academic_year: 2026,
                            created_at: "2026-03-20T00:00:00Z",
                            raw_json: {
                              academic_year: 2026,
                              names: ["機械学習特論", "情報セキュリティ特論"],
                            },
                          },
                        ],
                        error: null,
                      }),
                  }
                },
              }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      if (table === "courses") {
        return {
          update: (payload: Record<string, unknown>) => ({
            eq: () => ({
              eq: () => {
                resetDone = true
                return Promise.resolve({ error: null })
              },
            }),
            in: (_col: string, ids: string[]) => {
              if (payload.advance_enrollment === true) {
                updatedIds.push(...ids)
              }
              return Promise.resolve({ error: null })
            },
          }),
          select: () => ({
            eq: () => ({
              eq: () => Promise.resolve({
                data: [
                  { id: "c-ml-1", name: "機械学習特論" },
                  { id: "c-ml-2", name: "機械学習特論" },
                  { id: "c-sec-1", name: "情報セキュリティ特論" },
                ],
                error: null,
              }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      return {} as unknown as ReturnType<typeof supabase.from>
    })

    const result = await replayApprovedAdvanceEnrollment(2026)
    expect(queriedType).toBe("advance_enrollment")
    expect(queriedStatus).toBe("approved")
    expect(queriedYear).toBe(2026)
    expect(resetDone).toBe(true)
    expect(updatedIds).toEqual(["c-ml-1", "c-ml-2", "c-sec-1"])
    expect(result.extractionCount).toBe(1)
    expect(result.courseCount).toBe(3)

    mockFrom.mockRestore()
  })
})

describe("approveExtraction with Timetable auto-replay", () => {
  it("automatically replays both approved changelogs and advance enrollments", async () => {
    const mockFrom = spyOn(supabase, "from").mockImplementation((table: string) => {
      if (table === "extractions") {
        return {
          update: () => ({
            eq: () => Promise.resolve({ error: null }),
          }),
          select: () => ({
            eq: (col1: string, val1: string) => ({
              eq: () => ({
                eq: () => ({
                  order: () => {
                    if (val1 === "changelog") {
                      return Promise.resolve({
                        data: [
                          {
                            id: "ch-replay-1",
                            academic_year: 2026,
                            semester: "spring",
                            created_at: "2026-04-10T00:00:00Z",
                            raw_json: { academic_year: 2026, changes: [] },
                          },
                        ],
                        error: null,
                      })
                    }
                    if (val1 === "advance_enrollment") {
                      return Promise.resolve({
                        data: [
                          {
                            id: "adv-replay-1",
                            academic_year: 2026,
                            created_at: "2026-03-25T00:00:00Z",
                            raw_json: { academic_year: 2026, names: ["時間割科目"] },
                          },
                        ],
                        error: null,
                      })
                    }
                    return Promise.resolve({ data: [], error: null })
                  },
                }),
              }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      if (table === "courses") {
        return {
          upsert: () => ({
            select: () => Promise.resolve({ data: [{ id: "c-1", code: "tt101" }], error: null }),
          }),
          update: () => ({
            eq: () => ({
              eq: () => Promise.resolve({ error: null }),
            }),
            in: () => Promise.resolve({ error: null }),
          }),
          select: () => ({
            eq: () => ({
              eq: () => Promise.resolve({ data: [{ id: "c-1", name: "時間割科目" }], error: null }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      if (table === "schedules" || table === "course_targets") {
        return {
          delete: () => ({
            eq: () => Promise.resolve({ error: null }),
            in: () => Promise.resolve({ error: null }),
          }),
          insert: () => Promise.resolve({ error: null }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      return {} as unknown as ReturnType<typeof supabase.from>
    })

    const timetableRaw: TimetableRawJson = {
      courses: [
        {
          code: "tt101",
          name: "時間割科目",
          instructors: ["山田"],
        },
      ],
      academic_year: 2026,
    }

    const result = await approveExtraction("ext-tt-1", "timetable", timetableRaw)

    expect(result.ok).toBe(true)
    expect(result.count).toBe(1)
    expect(result.replayedChangelogs).toBe(1)
    expect(result.replayedAdvanceEnrollments).toBe(1)

    mockFrom.mockRestore()
  })
})
