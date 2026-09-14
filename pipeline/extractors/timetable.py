"""Timetable PDF extractor."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import List, Optional

import pdfplumber
import pypdf
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from pipeline.adapters.gemini import run_with_model_fallback
from pipeline.config import Config
from pipeline.models import (
    COURSE_CODE_PATTERN,
    VALID_DAYS,
    VALID_TERMS,
    CourseTarget,
    ExtractedCourse,
    PageClassification,
    Schedule,
    Semester,
)

logger = logging.getLogger(__name__)


class _TablePage:
    __slots__ = ("rows", "is_intensive", "semester")

    def __init__(
        self,
        rows: list[list[str]],
        is_intensive: bool,
        semester: Semester | None,
    ) -> None:
        self.rows = rows
        self.is_intensive = is_intensive
        self.semester = semester


class RawTarget(BaseModel):
    target_code: Optional[str] = Field(None, description="Target code")
    target_name: Optional[str] = Field(None, description="Target name")
    note: Optional[str] = Field(None, description="Target note")


class RawPairedSlot(BaseModel):
    day: Optional[str] = Field(None, description="Day of the week")
    period: Optional[int] = Field(None, description="Period")


class RawCourse(BaseModel):
    code: str = Field(..., description="Course code")
    name: str = Field(..., description="Course name")
    instructors: List[str] = Field(..., description="Instructors list")
    year_level: Optional[int] = Field(None, description="Year level")
    class_section: Optional[str] = Field(None, description="Class section")
    term: Optional[str] = Field(None, description="Term")
    day: Optional[str] = Field(None, description="Day")
    period: Optional[int] = Field(None, description="Period")
    room: Optional[str] = Field(None, description="Room")
    target_raw: Optional[str] = Field(None, description="Raw target text")
    targets: Optional[List[RawTarget]] = Field(None, description="Structured targets")
    notes: Optional[str] = Field(None, description="Notes")
    paired_slots: Optional[List[RawPairedSlot]] = Field(None, description="Paired slots")


class TimetableResponse(BaseModel):
    courses: List[RawCourse] = Field(..., description="List of extracted courses")


def infer_term_from_code(
    code: str,
    day: str | None = None,
    period: int | None = None,
    has_paired_slots: bool = False,
) -> str | None:
    """Infer academic term from course code prefix and schedule presence.

    TCU course code structure:
    - smaa: 前期前 (1Q)
    - smab: 前期後 (2Q)
    - smaz: 前期 (if regular weekly schedule exists) or 前集中 (if no weekly slots)
    - smba: 後期前 (3Q)
    - smbb: 後期後 (4Q)
    - smbz: 後期 (if regular weekly schedule exists) or 後集中 (if no weekly slots)
    """
    if len(code) >= 4:
        prefix = code[:4].lower()
        if prefix.endswith("aa"):
            return "前期前"
        elif prefix.endswith("ab"):
            return "前期後"
        elif prefix.endswith("az"):
            has_regular = has_paired_slots or (
                bool(day) and day != "-" and period is not None and 1 <= period <= 5
            )
            return "前期" if has_regular else "前集中"
        elif prefix.endswith("ba"):
            return "後期前"
        elif prefix.endswith("bb"):
            return "後期後"
        elif prefix.endswith("bz"):
            has_regular = has_paired_slots or (
                bool(day) and day != "-" and period is not None and 1 <= period <= 5
            )
            return "後期" if has_regular else "後集中"
    return None


def _raw_to_extracted_course(
    raw: dict, semester: Semester | None = None
) -> ExtractedCourse | None:
    code = str(raw.get("code", "")).strip()
    if not code or not COURSE_CODE_PATTERN.match(code):
        logger.debug("Skipping invalid/missing course code: %r", code)
        return None

    name = str(raw.get("name", "")).strip()
    instructors = [
        str(i).strip() for i in raw.get("instructors", []) if str(i).strip()
    ] or ["未定"]
    year_level = int(raw.get("year_level", 1) or 1)
    class_section = str(raw.get("class_section", "") or "").strip()
    notes = str(raw.get("notes", "") or "").strip()
    target_raw = str(raw.get("target_raw", "") or "").strip()

    targets: list[CourseTarget] = []
    for target in raw.get("targets", []) or []:
        tc = str(target.get("target_code", "")).strip()
        tn = str(target.get("target_name", "")).strip()
        if tc or tn:
            targets.append(
                CourseTarget(
                    target_code=tc,
                    target_name=tn,
                    note=str(target.get("note", "") or "").strip(),
                )
            )

    day = str(raw.get("day", "") or "").strip()
    room = str(raw.get("room", "") or "").strip()
    period_raw = raw.get("period")
    period_int: int | None = None
    if period_raw is not None:
        try:
            period_int = int(period_raw)
        except (ValueError, TypeError):
            pass

    has_paired = bool(raw.get("paired_slots"))
    has_regular_sched = has_paired or (
        bool(day) and day in VALID_DAYS and period_int is not None and 1 <= period_int <= 5
    )

    schedules: list[Schedule] = []
    term = str(raw.get("term", "") or "").strip()
    if term in VALID_TERMS:
        # Correct false intensive term when regular weekly schedule exists
        if has_regular_sched:
            if term == "前集中":
                term = "前期"
            elif term == "後集中":
                term = "後期"
    else:
        inferred = infer_term_from_code(
            code,
            day=day,
            period=period_int,
            has_paired_slots=has_paired,
        )
        if inferred:
            term = inferred

    if not semester:
        if term:
            if term.startswith("前期") or term.startswith("前集中") or term == "通年":
                semester = Semester.SPRING
            elif term.startswith("後期") or term.startswith("後集中"):
                semester = Semester.FALL
        if not semester and len(code) >= 3:
            if code[2].lower() == "a":
                semester = Semester.SPRING
            elif code[2].lower() == "b":
                semester = Semester.FALL

    if raw.get("paired_slots"):
        for slot in raw["paired_slots"]:
            slot_day = str(slot.get("day", "")).strip()
            slot_period = slot.get("period")
            if (
                slot_day in VALID_DAYS
                and isinstance(slot_period, int)
                and 1 <= slot_period <= 5
            ):
                schedules.append(
                    Schedule(day=slot_day, period=slot_period)
                )
    elif day and period_int is not None:
        if day in VALID_DAYS and 1 <= period_int <= 5:
            schedules.append(Schedule(day=day, period=period_int))

    try:
        return ExtractedCourse(
            code=code,
            name=name,
            instructors=instructors,
            year_level=year_level,
            class_section=class_section,
            semester=semester,
            term=term or None,
            room=room or None,
            schedules=schedules,
            target_raw=target_raw,
            targets=targets,
            notes=notes,
        )
    except Exception as exc:
        logger.warning("Failed to construct ExtractedCourse for %s: %s", code, exc)
        return None


def deduplicate_courses(courses: list[ExtractedCourse]) -> list[ExtractedCourse]:
    by_code: dict[str, ExtractedCourse] = {}
    for course in courses:
        if course.code in by_code:
            existing = by_code[course.code]
            existing_slots = {(s.day, s.period) for s in existing.schedules}
            for sched in course.schedules:
                key = (sched.day, sched.period)
                if key not in existing_slots:
                    existing.schedules.append(sched)
                    existing_slots.add(key)
        else:
            by_code[course.code] = course
    return list(by_code.values())


def extract_courses_from_pdf(
    pdf_bytes: bytes,
    classifications: list[PageClassification] | None = None,
) -> list[ExtractedCourse]:
    del classifications

    table_page_indices: list[int] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for idx, page in enumerate(pdf.pages):
            if page.extract_tables():
                text = page.extract_text() or ""
                if "講義コード" in text or "科目名" in text:
                    table_page_indices.append(idx)

    if not table_page_indices:
        logger.warning("No table pages detected via pdfplumber; returning empty.")
        return []

    logger.info("Found %d table pages to process page-by-page.", len(table_page_indices))
    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    all_courses: list[ExtractedCourse] = []

    prompt = """以下は東京都市大学 総合理工学研究科の授業時間表 PDF の1ページです。
全ての行を構造化 JSON（TimetableResponse）として出力してください。

ルール:
- 結合セル（曜日・時限・学期・年クラスが空欄）は直前の行の値を引き継いでください
- 学期（term）は PDF の「学期」列の値を正確に抽出してください。
  有効な学期: 「前期前」「前期後」「前期」「前集中」「後期前」「後期後」「後期」「後集中」「通年」
  ※ 曜日・時限がある通常の講義（例: 火2, 木3 等）で学期セルが空欄（結合セル）の場合、決して「前集中」「後集中」とせず、直前の学期（通常は「前期」または「後期」）を引き継いでください。
  ※「前集中」「後集中」は、定期的な曜日・時限のない集中講義のみに適用されます。
- 「対開講(月1,木1)」のような記述がある場合は paired_slots に全スロットをリストアップしてください
- 受講対象は target_raw に原文を、targets に構造化した情報を入れてください
- instructors が複数の場合は配列に分けてください
- 集中講義は day, period が空になります（paired_slots も空）
- 講義コードが無効な行はスキップしてください（形式: sm[英字2][数字6]、例: smab020161）
"""

    for idx in table_page_indices:
        logger.info("Processing page %d with Gemini...", idx + 1)
        writer = pypdf.PdfWriter()
        writer.add_page(reader.pages[idx])
        single_page_pdf = BytesIO()
        writer.write(single_page_pdf)
        single_page_bytes = single_page_pdf.getvalue()

        def _generate_page(model_name: str) -> str:
            resp = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=single_page_bytes, mime_type="application/pdf"),
                    prompt,
                ],
                config=genai.types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=65536,
                    response_mime_type="application/json",
                    response_json_schema=TimetableResponse.model_json_schema(),
                ),
            )
            if not resp.text:
                raise ValueError(f"Gemini response for page {idx + 1} did not include text.")
            return resp.text

        try:
            raw_text = run_with_model_fallback(
                primary_model=Config.GEMINI_MODEL,
                fallback_model=Config.GEMINI_FALLBACK_MODEL,
                runner=_generate_page,
                logger=logger,
                client=client,
            )
            parsed = TimetableResponse.model_validate_json(raw_text)
            for course in parsed.courses:
                extracted = _raw_to_extracted_course(course.model_dump())
                if extracted:
                    all_courses.append(extracted)
        except Exception as exc:
            logger.error("Failed processing page %d: %s", idx + 1, exc)

    # Enrich courses with deterministic room map from PDF tables
    try:
        room_map = extract_room_map_from_pdf(pdf_bytes)
        for course in all_courses:
            if not course.room and course.code in room_map:
                course.room = room_map[course.code]
    except Exception as exc:
        logger.warning("Failed to extract room map from PDF: %s", exc)

    return deduplicate_courses(all_courses)


def merge_room_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not merged:
            merged.append(line)
        elif line.startswith(",") or merged[-1].endswith(","):
            merged[-1] += line
        elif line in ("イトクラス", "議室", "学院製図室", "階）", "階)", "室(10号館3", "（2号館3"):
            merged[-1] += line
        elif merged[-1].endswith(("サテラ", "2階会", "2階大", "機械系実験", "臨床実習室", "（2号館3")):
            merged[-1] += line
        else:
            merged.append(line)
    return merged


def extract_room_map_from_pdf(pdf_bytes: bytes) -> dict[str, str]:
    """Extract mapping of course code -> classroom directly from PDF tables."""
    code_to_room: dict[str, str] = {}
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                header = table[0]
                code_col = None
                room_col = None
                for idx, col in enumerate(header):
                    if col and "コード" in col:
                        code_col = idx
                    elif col and "教室" in col:
                        room_col = idx
                if code_col is None or room_col is None:
                    continue

                for row in table[1:]:
                    if len(row) <= max(code_col, room_col):
                        continue
                    code_cell = row[code_col] or ""
                    room_cell = row[room_col] or ""
                    codes = [
                        c.strip()
                        for c in code_cell.splitlines()
                        if c.strip().startswith("sm")
                    ]
                    if not codes:
                        continue
                    cleaned_rooms = merge_room_lines(
                        [r.strip() for r in room_cell.splitlines() if r.strip()]
                    )
                    if len(codes) == len(cleaned_rooms):
                        for c, rm in zip(codes, cleaned_rooms):
                            if rm and rm != "-":
                                code_to_room[c] = rm
                    elif len(codes) == 1:
                        rm = "".join(cleaned_rooms)
                        if rm and rm != "-":
                            code_to_room[codes[0]] = rm
    return code_to_room
