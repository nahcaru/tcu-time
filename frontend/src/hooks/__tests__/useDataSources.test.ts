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
    })
    expect(result.fall).toEqual({
      type: "syllabus",
      isTentative: true,
      updatedAt: "2026-03-18T12:00:00Z",
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
        semester: "spring",
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

    const result = resolveDataSources(extractions, courses)

    expect(result.spring).toEqual({
      type: "timetable",
      isTentative: false,
      updatedAt: "2026-04-08T09:00:00Z",
    })
    expect(result.fall).toEqual({
      type: "timetable",
      isTentative: true,
      updatedAt: "2026-04-08T09:00:00Z",
    })
    // Successfully detected via extractions even without source_type === 'changelog'
    expect(result.hasChangelog).toBe(true)
    expect(result.changelogUpdatedAt).toBe("2026-04-12T14:00:00Z")
    expect(result.hasAdvance).toBe(true)
    expect(result.advanceUpdatedAt).toBe("2026-04-10T11:00:00Z")
  })

  it("handles September lifecycle: Fall definitive", () => {
    const extractions = [
      {
        pdf_type: "timetable",
        semester: "fall",
        is_tentative: false,
        status: "approved",
        created_at: "2026-09-15T08:00:00Z",
        updated_at: "2026-09-15T08:00:00Z",
      },
      {
        pdf_type: "timetable",
        semester: "spring",
        is_tentative: false,
        status: "approved",
        created_at: "2026-04-08T09:00:00Z",
        updated_at: "2026-04-08T09:00:00Z",
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

    expect(result.spring?.isTentative).toBe(false)
    expect(result.fall?.isTentative).toBe(false)
    expect(result.fall?.type).toBe("timetable")
    expect(result.fall?.updatedAt).toBe("2026-09-15T08:00:00Z")
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
  })
})
