import { describe, expect, it } from "bun:test"
import { resolveDataSources } from "../use-data-sources"

describe("resolveDataSources", () => {
  it("returns empty sources when no extractions or courses exist", () => {
    const result = resolveDataSources([], [])
    expect(result.spring).toBeNull()
    expect(result.fall).toBeNull()
    expect(result.hasChangelog).toBe(false)
    expect(result.changelogUpdatedAt).toBeNull()
    expect(result.hasAdvance).toBe(false)
    expect(result.advanceUpdatedAt).toBeNull()
  })

  it("handles March lifecycle: Spring tentative (timetable) + Fall temporary (syllabus)", () => {
    const extractions = [
      {
        pdf_type: "timetable",
        semester: "spring",
        is_tentative: true,
        status: "approved",
        created_at: "2026-03-18T10:00:00Z",
        updated_at: "2026-03-18T10:00:00Z",
      },
    ]
    const courses = [
      {
        source_type: "timetable",
        semester: "spring",
        is_tentative: true,
        advance_enrollment: false,
        updated_at: "2026-03-18T10:00:00Z",
      },
      {
        source_type: "syllabus",
        semester: "fall",
        is_tentative: true,
        advance_enrollment: false,
        updated_at: "2026-03-18T12:00:00Z",
      },
    ]

    const result = resolveDataSources(extractions, courses)

    expect(result.spring).toEqual({
      type: "timetable",
      isTentative: true,
      updatedAt: "2026-03-18T10:00:00Z",
      hasChangelog: false,
      changelogUpdatedAt: null,
    })
    expect(result.fall).toEqual({
      type: "syllabus",
      isTentative: true,
      updatedAt: "2026-03-18T12:00:00Z",
      hasChangelog: false,
      changelogUpdatedAt: null,
    })
    expect(result.hasChangelog).toBe(false)
    expect(result.hasAdvance).toBe(false)
    expect(result.hasSyllabus).toBe(true)
  })

  it("handles April lifecycle: Spring definitive + Fall tentative + Changelog + Advance", () => {
    const extractions = [
      {
        pdf_type: "changelog",
        semester: "spring",
        is_tentative: false,
        status: "approved",
        created_at: "2026-04-12T14:00:00Z",
        updated_at: "2026-04-12T14:00:00Z",
      },
      {
        pdf_type: "advance_enrollment",
        semester: null,
        is_tentative: false,
        status: "approved",
        created_at: "2026-04-10T11:00:00Z",
        updated_at: "2026-04-10T11:00:00Z",
      },
      {
        pdf_type: "timetable",
        semester: "spring",
        is_tentative: false,
        status: "approved",
        created_at: "2026-04-08T09:00:00Z",
        updated_at: "2026-04-08T09:00:00Z",
      },
      {
        pdf_type: "timetable",
        semester: "fall",
        is_tentative: true,
        status: "approved",
        created_at: "2026-04-08T09:00:00Z",
        updated_at: "2026-04-08T09:00:00Z",
      },
    ]

    // Note: changelog only updated existing courses, so no course has source_type === 'changelog'
    const courses = [
      {
        source_type: "timetable",
        semester: "spring",
        is_tentative: false,
        advance_enrollment: false,
        updated_at: "2026-04-12T14:00:00Z",
      },
      {
        source_type: "timetable",
        semester: "fall",
        is_tentative: true,
        advance_enrollment: false,
        updated_at: "2026-04-08T09:00:00Z",
      },
    ]

    const result = resolveDataSources(extractions, courses, 2026)

    expect(result.targetYear).toBe(2026)
    expect(result.spring).toEqual({
      type: "timetable",
      isTentative: false,
      updatedAt: "2026-04-08T09:00:00Z",
      hasChangelog: true,
      changelogUpdatedAt: "2026-04-12T14:00:00Z",
    })
    expect(result.fall).toEqual({
      type: "timetable",
      isTentative: true,
      updatedAt: "2026-04-08T09:00:00Z",
      hasChangelog: false,
      changelogUpdatedAt: null,
    })
    // Successfully detected via extractions even without source_type === 'changelog'
    expect(result.hasChangelog).toBe(true)
    expect(result.changelogUpdatedAt).toBe("2026-04-12T14:00:00Z")
    expect(result.hasAdvance).toBe(true)
    expect(result.advanceUpdatedAt).toBe("2026-04-10T11:00:00Z")
  })

  it("handles September lifecycle: Fall definitive and prioritizes published_at / raw_json over created_at", () => {
    const extractions = [
      {
        pdf_type: "timetable",
        semester: "fall",
        is_tentative: false,
        status: "approved",
        published_at: "2026-09-10T18:43:34+09:00", // actual release date
        created_at: "2026-09-13T14:51:24Z",        // crawler date
        updated_at: "2026-09-15T06:28:26Z",        // approval date
      },
      {
        pdf_type: "timetable",
        semester: "spring",
        is_tentative: false,
        status: "approved",
        raw_json: { published_at: "2026-04-15T18:09:20+09:00" }, // via raw_json fallback
        created_at: "2026-04-15T21:58:18Z",
        updated_at: "2026-09-14T18:01:26Z",
      },
      {
        pdf_type: "advance_enrollment",
        semester: "spring", // even if DB erroneously stored 'spring'
        is_tentative: false,
        status: "approved",
        published_at: "2026-03-26T14:51:00+09:00",
        created_at: "2026-03-27T04:10:17Z",
      },
    ]
    const courses = [
      {
        source_type: "timetable",
        semester: "spring",
        is_tentative: false,
        advance_enrollment: false,
        updated_at: "2026-04-17T09:00:00Z",
      },
      {
        source_type: "timetable",
        semester: "fall",
        is_tentative: false,
        advance_enrollment: false,
        updated_at: "2026-09-15T08:00:00Z",
      },
    ]

    const result = resolveDataSources(extractions, courses)

    expect(result.spring?.isTentative).toBe(false)
    expect(result.spring?.updatedAt).toBe("2026-04-15T18:09:20+09:00") // 4/15 via raw_json
    expect(result.fall?.isTentative).toBe(false)
    expect(result.fall?.type).toBe("timetable")
    expect(result.fall?.updatedAt).toBe("2026-09-10T18:43:34+09:00") // 9/10 via published_at
    expect(result.hasAdvance).toBe(true)
    expect(result.advanceUpdatedAt).toBe("2026-03-26T14:51:00+09:00") // 3/26 common
  })

  it("detects changelog per semester", () => {
    const extractions = [
      {
        pdf_type: "changelog",
        semester: "fall",
        is_tentative: false,
        status: "approved",
        created_at: "2026-09-20T10:00:00Z",
        updated_at: "2026-09-20T12:00:00Z",
      },
    ]
    const courses = [
      {
        source_type: "timetable",
        semester: "spring",
        is_tentative: false,
        advance_enrollment: false,
        updated_at: "2026-04-08T09:00:00Z",
      },
      {
        source_type: "timetable",
        semester: "fall",
        is_tentative: false,
        advance_enrollment: false,
        updated_at: "2026-09-15T08:00:00Z",
      },
    ]

    const result = resolveDataSources(extractions, courses)

    expect(result.spring?.hasChangelog).toBe(false)
    expect(result.fall?.hasChangelog).toBe(true)
    expect(result.fall?.changelogUpdatedAt).toBe("2026-09-20T10:00:00Z")
  })

  it("detects changelog and advance from course records as fallback", () => {
    const result = resolveDataSources(
      [],
      [
        {
          source_type: "changelog",
          semester: "spring",
          is_tentative: false,
          advance_enrollment: true,
          updated_at: "2026-04-15T10:00:00Z",
        },
      ]
    )

    expect(result.hasChangelog).toBe(true)
    expect(result.hasAdvance).toBe(true)
    expect(result.spring?.hasChangelog).toBe(true)
  })
})
