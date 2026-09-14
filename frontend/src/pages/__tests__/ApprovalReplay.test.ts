import { describe, expect, it, spyOn } from "bun:test"
import {
  approveExtraction,
  replayApprovedChangelogs,
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

describe("approveExtraction with Timetable auto-replay", () => {
  it("automatically replays approved changelogs and returns replayed count", async () => {
    const mockFrom = spyOn(supabase, "from").mockImplementation((table: string) => {
      if (table === "extractions") {
        return {
          update: () => ({
            eq: () => Promise.resolve({ error: null }),
          }),
          select: () => ({
            eq: () => ({
              eq: () => ({
                eq: () => ({
                  order: () =>
                    Promise.resolve({
                      data: [
                        {
                          id: "ch-replay-1",
                          academic_year: 2026,
                          semester: "spring",
                          created_at: "2026-04-10T00:00:00Z",
                          raw_json: {
                            academic_year: 2026,
                            changes: [],
                          },
                        },
                      ],
                      error: null,
                    }),
                }),
              }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      if (table === "courses") {
        return {
          upsert: () => ({
            select: () => ({
              single: () => Promise.resolve({ data: { id: "c-1" }, error: null }),
            }),
          }),
        } as unknown as ReturnType<typeof supabase.from>
      }

      if (table === "schedules" || table === "course_targets") {
        return {
          delete: () => ({
            eq: () => Promise.resolve({ error: null }),
          }),
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

    mockFrom.mockRestore()
  })
})
