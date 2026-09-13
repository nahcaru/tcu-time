import { describe, expect, it } from "bun:test"
import { inferTerm } from "../../lib/termInference"

describe("inferTerm", () => {
  it("preserves already valid term", () => {
    expect(inferTerm({ code: "smba010071", name: "熱工学特論", instructors: [], term: "後期前" })).toBe("後期前")
    expect(inferTerm({ code: "smaa050061", name: "コロイド化学特論", instructors: [], term: "前期前" })).toBe("前期前")
  })

  it("infers term from course code prefix", () => {
    expect(inferTerm({ code: "smaa010011", name: "Test", instructors: [] })).toBe("前期前")
    expect(inferTerm({ code: "smab020161", name: "Test", instructors: [] })).toBe("前期後")
    expect(inferTerm({ code: "smaz060101", name: "Test", instructors: [] })).toBe("前集中")
    expect(inferTerm({ code: "smba080041", name: "水理学特論", instructors: [] })).toBe("後期前")
    expect(inferTerm({ code: "smbb030021", name: "電気磁気学特論", instructors: [] })).toBe("後期後")
    expect(inferTerm({ code: "smbz050051", name: "結晶化学特論", instructors: [] })).toBe("後集中")
  })

  it("infers term from extraction semester when code has no specific sub-term", () => {
    expect(inferTerm({ code: "ymaa000001", name: "Test", instructors: [] }, "fall")).toBe("後期前")
    expect(inferTerm({ code: "ymaa000001", name: "Test", instructors: [] }, "spring")).toBe("前期")
  })
})
