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

    schedules: list[Schedule] = []
    term = str(raw.get("term", "") or "").strip()
    day = str(raw.get("day", "") or "").strip()
    room = str(raw.get("room", "") or "").strip()
    period_raw = raw.get("period")

    if not semester and term:
        if term.startswith("前期") or term.startswith("前集中") or term == "通年":
            semester = Semester.SPRING
        elif term.startswith("後期") or term.startswith("後集中"):
            semester = Semester.FALL

    if raw.get("paired_slots"):
        for slot in raw["paired_slots"]:
            slot_day = str(slot.get("day", "")).strip()
            slot_period = slot.get("period")
            if (
                slot_day in VALID_DAYS
                and isinstance(slot_period, int)
                and 1 <= slot_period <= 5
                and term in VALID_TERMS
            ):
                schedules.append(
                    Schedule(term=term, day=slot_day, period=slot_period, room=room)
                )
    elif day and period_raw is not None:
        try:
            period = int(period_raw)
            if day in VALID_DAYS and 1 <= period <= 5 and term in VALID_TERMS:
                schedules.append(Schedule(term=term, day=day, period=period, room=room))
        except (ValueError, TypeError):
            pass

    try:
        return ExtractedCourse(
            code=code,
            name=name,
            instructors=instructors,
            year_level=year_level,
            class_section=class_section,
            semester=semester,
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

        try:
            response = client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=single_page_bytes, mime_type="application/pdf"),
                    prompt,
                ],
                config=genai.types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=65536,
                    thinking_config=types.ThinkingConfig(thinking_level="LOW"),
                    response_mime_type="application/json",
                    response_json_schema=TimetableResponse.model_json_schema(),
                ),
            )

            if not response.text:
                logger.warning("Gemini response for page %d did not include text.", idx + 1)
                continue

            parsed = TimetableResponse.model_validate_json(response.text)
            for course in parsed.courses:
                extracted = _raw_to_extracted_course(course.model_dump())
                if extracted:
                    all_courses.append(extracted)
        except Exception as exc:
            logger.error("Failed processing page %d: %s", idx + 1, exc)

    return deduplicate_courses(all_courses)

