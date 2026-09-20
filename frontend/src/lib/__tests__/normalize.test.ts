import { describe, expect, it } from "bun:test"
import {
  normalizeSearchText,
  normalizeInstructorName,
  normalizeCourseName,
  normalizeRoom,
  normalizeNote,
} from "../normalize"

describe("normalizeSearchText", () => {
  it("normalizes fullwidth characters, brackets, slashes, and spaces", () => {
    expect(normalizeSearchText("ＰＰＰ／ＰＦＩ")).toBe("ppp/pfi")
    expect(normalizeSearchText("特別講義（基礎Ｉ）")).toBe("特別講義(基礎i)")
    expect(normalizeSearchText("三宅\u3000弘晃")).toBe("三宅 弘晃")
    expect(normalizeSearchText("  先端Ｘ線  ")).toBe("先端x線")
  })
})

describe("normalizeInstructorName", () => {
  it("converts fullwidth space to single halfwidth space", () => {
    expect(normalizeInstructorName("三宅\u3000弘晃")).toBe("三宅 弘晃")
    expect(normalizeInstructorName("  伊藤 \u3000 和也 ")).toBe("伊藤 和也")
    expect(normalizeInstructorName("ボルジロフスカヤアンナ")).toBe(
      "ボルジロフスカヤアンナ"
    )
  })
})

describe("normalizeCourseName", () => {
  it("normalizes course name characters and punctuation", () => {
    expect(normalizeCourseName("ＰＰＰ／ＰＦＩ特論")).toBe("PPP/PFI特論")
    expect(normalizeCourseName("特別講義（基礎I）")).toBe("特別講義(基礎I)")
    expect(normalizeCourseName("Artificial Intelligence,Adv.")).toBe(
      "Artificial Intelligence, Adv."
    )
    expect(normalizeCourseName("先端Ｘ線分析特論")).toBe("先端X線分析特論")
  })
})

describe("normalizeRoom", () => {
  it("normalizes parentheses in room", () => {
    expect(normalizeRoom("臨床実習室（2号館3階）")).toBe("臨床実習室(2号館3階)")
  })
})

describe("normalizeNote", () => {
  it("normalizes tildes and parentheses", () => {
    expect(normalizeNote("～25VLSI回路設計特論")).toBe("~25VLSI回路設計特論")
    expect(normalizeNote("対開講（月2,火2）")).toBe("対開講(月2,火2)")
  })
})
