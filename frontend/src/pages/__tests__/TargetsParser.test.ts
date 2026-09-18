import { describe, expect, it } from "bun:test"
import {
  parseSingleTarget,
  parseTargetsString,
  formatTargetsString,
} from "@/lib/approvalService"

describe("TargetsParser", () => {
  it("parses code and name correctly", () => {
    expect(parseSingleTarget("00共通")).toEqual({
      target_code: "00",
      target_name: "共通",
      note: "",
    })

    expect(parseSingleTarget("02機械")).toEqual({
      target_code: "02",
      target_name: "機械",
      note: "",
    })

    expect(parseSingleTarget("10A情報科学科")).toEqual({
      target_code: "10A",
      target_name: "情報科学科",
      note: "",
    })
  })

  it("parses note in parentheses", () => {
    expect(parseSingleTarget("00共通（全専攻）")).toEqual({
      target_code: "00",
      target_name: "共通",
      note: "全専攻",
    })

    expect(parseSingleTarget("08都市工学 (専攻)")).toEqual({
      target_code: "08",
      target_name: "都市工学",
      note: "専攻",
    })
  })

  it("parses multiple targets string", () => {
    const parsed = parseTargetsString("00共通、10情報科学科, 08都市工学(専攻)")
    expect(parsed).toEqual([
      { target_code: "00", target_name: "共通", note: "" },
      { target_code: "10", target_name: "情報科学科", note: "" },
      { target_code: "08", target_name: "都市工学", note: "専攻" },
    ])
  })

  it("formats targets back into string", () => {
    const formatted = formatTargetsString([
      { target_code: "00", target_name: "共通", note: "" },
      { target_code: "10", target_name: "情報科学科", note: "" },
      { target_code: "08", target_name: "都市工学", note: "専攻" },
    ])
    expect(formatted).toBe("00共通, 10情報科学科, 08都市工学（専攻）")
  })
})
