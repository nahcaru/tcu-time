"""Extractor: PDF → structured course data.

Pipeline: PDF → pdfplumber tables → merge multiline rows → parse rows → deduplicate
           → Gemini fallback (optional, for ambiguous rows) → validate → output.

The PDF has two table formats:
  - Regular pages (10 cols): 曜, 限, 学期, 年クラス, 科目名, 担当者, 講義コード, 教室, 受講対象, 備考
  - Intensive pages (7 cols): 学期, 年クラス, 科目名, 担当者, 講義コード, 教室, 受講対象
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from io import BytesIO
from typing import Any

import pdfplumber
import requests

from pipeline.config import Config
from pipeline.models import (
    COURSE_CODE_PATTERN,
    VALID_DAYS,
    VALID_TERMS,
    CourseTarget,
    ExtractedCourse,
    ExtractionResult,
    Schedule,
)

logger = logging.getLogger(__name__)

# Column indices for 10-column (regular) tables
_R_DAY = 0
_R_PERIOD = 1
_R_TERM = 2
_R_YEAR_CLASS = 3
_R_NAME = 4
_R_INSTRUCTOR = 5
_R_CODE = 6
_R_ROOM = 7
_R_TARGET = 8
_R_NOTE = 9

# Column indices for 7-column (intensive) tables
_I_TERM = 0
_I_YEAR_CLASS = 1
_I_NAME = 2
_I_INSTRUCTOR = 3
_I_CODE = 4
_I_ROOM = 5
_I_TARGET = 6

# Page ranges (0-indexed)
FRONT_REGULAR_PAGES = [6, 7]   # Pages 7-8: regular front-semester courses
FRONT_INTENSIVE_PAGES = [8]    # Page 9: intensive front-semester courses
BACK_REGULAR_PAGES = [9, 10]   # Pages 10-11: regular back-semester courses
BACK_INTENSIVE_PAGES = [11]    # Page 12: intensive back-semester courses


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------


def _normalize(text: str | None) -> str:
    """Normalize text: NFKC unicode, strip whitespace."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def _fullwidth_to_half(text: str) -> str:
    """Convert full-width digits/letters to half-width."""
    return unicodedata.normalize("NFKC", text)


# ---------------------------------------------------------------------------
# Table extraction from PDF
# ---------------------------------------------------------------------------


def extract_tables_from_pdf(
    pdf_bytes: bytes,
) -> tuple[list[list[list[str]]], list[list[list[str]]]]:
    """Extract tables from the PDF.

    Returns (regular_tables, intensive_tables) where each is a list of
    raw table data (list of rows, each row a list of cell strings).
    """
    regular_tables: list[list[list[str]]] = []
    intensive_tables: list[list[list[str]]] = []

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        all_page_indices = (
            FRONT_REGULAR_PAGES
            + FRONT_INTENSIVE_PAGES
            + BACK_REGULAR_PAGES
            + BACK_INTENSIVE_PAGES
        )

        for page_idx in all_page_indices:
            if page_idx >= len(pdf.pages):
                logger.warning("Page %d not found in PDF (total: %d)", page_idx + 1, len(pdf.pages))
                continue

            page = pdf.pages[page_idx]
            tables = page.extract_tables(
                {"vertical_strategy": "text", "horizontal_strategy": "text"}
            )

            if not tables:
                logger.warning("No tables found on page %d", page_idx + 1)
                continue

            # Normalize all cells
            raw = [
                [_normalize(cell) for cell in row] for row in tables[0]
            ]

            # Skip header row (first row with column names)
            if raw and any(
                h in raw[0] for h in ("曜", "学期", "科目名")
            ):
                raw = raw[1:]

            is_intensive = page_idx in FRONT_INTENSIVE_PAGES + BACK_INTENSIVE_PAGES
            if is_intensive:
                intensive_tables.append(raw)
            else:
                regular_tables.append(raw)

    return regular_tables, intensive_tables


# ---------------------------------------------------------------------------
# Multi-line row merging
# ---------------------------------------------------------------------------


def _is_continuation_row(row: list[str], is_intensive: bool) -> bool:
    """Check if a row is a continuation of the previous row (wrapped text).

    A continuation row has no course code and no course name starting fresh.
    """
    if is_intensive:
        code_idx = _I_CODE
        name_idx = _I_NAME
    else:
        code_idx = _R_CODE
        name_idx = _R_NAME

    # If the code column has a valid code, it's definitely a new row
    code = row[code_idx] if code_idx < len(row) else ""
    if code and COURSE_CODE_PATTERN.match(code):
        return False

    # If the name column is empty or code is empty, it's likely a continuation
    name = row[name_idx] if name_idx < len(row) else ""

    # If both code and name are empty, it's a continuation
    if not code and not name:
        return True

    # If code is empty but name is not empty, check if it looks like a
    # continuation (e.g., second half of a wrapped name like "特論" or "ザイン]")
    if not code:
        return True

    return False


def merge_multiline_rows(
    rows: list[list[str]], is_intensive: bool
) -> list[list[str]]:
    """Merge continuation rows into their parent rows.

    The PDF wraps long text across multiple rows. Continuation rows have
    empty course code columns. We concatenate the text fields.
    """
    if not rows:
        return []

    merged: list[list[str]] = []
    current: list[str] | None = None

    # Instructor columns need newline separators when merging
    # (otherwise "佐藤 太郎" + "鈴木 花子" → "佐藤 太郎鈴木 花子")
    instructor_col = _I_INSTRUCTOR if is_intensive else _R_INSTRUCTOR

    for row in rows:
        if _is_continuation_row(row, is_intensive) and current is not None:
            # Merge text fields into current row
            for i in range(len(current)):
                if i < len(row) and row[i]:
                    if current[i]:
                        sep = "\n" if i == instructor_col else ""
                        current[i] = current[i] + sep + row[i]
                    else:
                        current[i] = row[i]
        else:
            if current is not None:
                merged.append(current)
            current = list(row)  # copy

    if current is not None:
        merged.append(current)

    return merged


# ---------------------------------------------------------------------------
# Carry-forward for merged cells
# ---------------------------------------------------------------------------


def carry_forward(
    rows: list[list[str]], is_intensive: bool
) -> list[list[str]]:
    """Fill in empty cells from the previous row (for merged cells).

    Carry-forward columns: 曜, 限, 学期, 年クラス (regular) or 学期, 年クラス (intensive).
    """
    if is_intensive:
        cf_cols = [_I_TERM, _I_YEAR_CLASS]
    else:
        cf_cols = [_R_DAY, _R_PERIOD, _R_TERM, _R_YEAR_CLASS]

    prev: dict[int, str] = {}
    for row in rows:
        for col in cf_cols:
            if col < len(row):
                if row[col]:
                    prev[col] = row[col]
                elif col in prev:
                    row[col] = prev[col]

    return rows


# ---------------------------------------------------------------------------
# Target parsing
# ---------------------------------------------------------------------------

# Pattern: 対象[XX専攻名] or 対象[XX専攻名/note]
_TARGET_PATTERN = re.compile(
    r"対象\[(.+?)\]"
)


def _is_note_text(text: str) -> bool:
    """Check if text looks like a note rather than a department name.

    Notes contain keywords like 以降, 入学生, 対象, 年度, のみ, etc.
    Department names are short and don't contain these patterns.
    """
    note_keywords = ("以降", "入学生", "対象", "年度", "のみ", "限定", "除く", "再履修")
    return any(kw in text for kw in note_keywords)


def parse_targets(target_raw: str) -> list[CourseTarget]:
    """Parse the 受講対象 column.

    Examples:
        "対象[09情報]" → [CourseTarget(target_code="09", target_name="情報")]
        "対象[02機械/23以降入学生対象]" → [CourseTarget(target_code="02", target_name="機械", note="23以降入学生対象")]
        "対象[7建築都市デザイン]" → [CourseTarget(target_code="7", target_name="建築都市デザイン")]
        "対象[00共通]" → [CourseTarget(target_code="00", target_name="共通")]
        "対象[10情報/0共通]" → two targets
    """
    match = _TARGET_PATTERN.search(target_raw)
    if not match:
        return []

    inner = match.group(1)
    targets: list[CourseTarget] = []

    # Split by "/" — could be note or multiple targets
    # Heuristic: if the part after / starts with a digit AND the remainder
    # looks like a department name (not a note), it's a new target.
    parts = inner.split("/")

    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue

        # Extract code (leading digits) and name
        code_match = re.match(r"^(\d+)", part)
        if code_match:
            code = code_match.group(1)
            name = part[len(code):]

            # If name looks like a note (e.g., "以降入学生対象"), treat the
            # whole part as a note on the previous target, not a new target.
            if _is_note_text(name) and targets:
                existing = targets[-1]
                targets[-1] = CourseTarget(
                    target_code=existing.target_code,
                    target_name=existing.target_name,
                    note=(existing.note + "/" + part).lstrip("/"),
                )
                i += 1
                continue

            # Check if next part is a note (doesn't start with digit)
            note = ""
            if i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                if next_part and (not re.match(r"^\d", next_part) or _is_note_text(next_part)):
                    note = next_part
                    i += 1

            targets.append(CourseTarget(
                target_code=code,
                target_name=name,
                note=note,
            ))
        else:
            # Non-digit start — probably a note for the previous target
            # like "～24入学生対象"
            if targets:
                existing = targets[-1]
                targets[-1] = CourseTarget(
                    target_code=existing.target_code,
                    target_name=existing.target_name,
                    note=(existing.note + "/" + part).lstrip("/"),
                )

        i += 1

    return targets


# ---------------------------------------------------------------------------
# Paired-slot parsing (対開講)
# ---------------------------------------------------------------------------

# Pattern: 対開講(月1,木1) or 対開講(火2,火3,火4)
_PAIRED_PATTERN = re.compile(r"対開講\((.+?)\)")


def parse_paired_slots(
    notes: str, term: str
) -> list[Schedule]:
    """Parse 対開講 from the notes column.

    Returns a list of Schedule objects for all paired slots.
    Example: "対開講(月1,木1)" with term="前期後" →
        [Schedule(term="前期後", day="月", period=1), Schedule(term="前期後", day="木", period=1)]
    """
    match = _PAIRED_PATTERN.search(notes)
    if not match:
        return []

    slots_str = _fullwidth_to_half(match.group(1))
    schedules: list[Schedule] = []

    for slot in slots_str.split(","):
        slot = slot.strip()
        if len(slot) >= 2:
            day = slot[0]
            try:
                period = int(slot[1:])
            except ValueError:
                logger.warning("Cannot parse period from paired slot: %s", slot)
                continue

            if day in VALID_DAYS and 1 <= period <= 5:
                schedules.append(Schedule(term=term, day=day, period=period))
            else:
                logger.warning("Invalid paired slot: day=%s period=%d", day, period)

    return schedules


# ---------------------------------------------------------------------------
# Instructor parsing
# ---------------------------------------------------------------------------


def _parse_instructors(instructor_raw: str) -> list[str]:
    """Parse instructor text into a list of individual names.

    Handles multi-line merging where:
    - New instructors are separated by \\n
    - Long names wrap across lines (fragment has no space and is a continuation)

    Names in the PDF always have a space between family and given name (e.g., "佐藤 太郎").
    Fragments without a space that follow a partial name get merged back.
    Special standalone names like "各教員", "未定", or names with ・ are kept as-is.
    """
    if not instructor_raw:
        return ["未定"]

    # Split on newlines (added during multiline merge)
    parts = [s.strip() for s in instructor_raw.split("\n") if s.strip()]
    if not parts:
        return [instructor_raw] if instructor_raw else ["未定"]

    # Merge fragments: if a part has no space and isn't a special name,
    # merge it into the previous entry
    merged: list[str] = []
    for part in parts:
        is_standalone = (
            " " in part          # Has family/given separator
            or "・" in part      # Foreign name format (e.g., "M・テイボン")
            or part in ("未定", "各教員")
            or not merged        # First entry is always standalone
        )
        if is_standalone:
            merged.append(part)
        else:
            # Fragment — merge into previous entry
            merged[-1] = merged[-1] + part

    return merged if merged else ["未定"]


# ---------------------------------------------------------------------------
# Row parsing
# ---------------------------------------------------------------------------


def parse_regular_row(row: list[str]) -> ExtractedCourse | None:
    """Parse a single merged regular-table row into an ExtractedCourse.

    Returns None if the row is invalid (no valid course code).
    """
    if len(row) < 10:
        return None

    code = row[_R_CODE].strip()
    if not code or not COURSE_CODE_PATTERN.match(code):
        return None

    day = row[_R_DAY].strip()
    period_str = row[_R_PERIOD].strip()
    term = row[_R_TERM].strip()
    year_class = row[_R_YEAR_CLASS].strip()
    name = row[_R_NAME].strip()
    instructor_raw = row[_R_INSTRUCTOR].strip()
    room = row[_R_ROOM].strip()
    target_raw = row[_R_TARGET].strip()
    notes = row[_R_NOTE].strip()

    # Parse year and class from combined column
    year_level = 1
    class_section = ""
    if year_class:
        # Could be "1", "1 一般", etc.
        parts = year_class.split()
        try:
            year_level = int(parts[0])
        except ValueError:
            pass
        if len(parts) > 1:
            class_section = parts[1]

    # Parse instructors
    instructors = _parse_instructors(instructor_raw)

    # Parse term validation
    if term not in VALID_TERMS:
        logger.warning("Invalid term '%s' for course %s, skipping", term, code)
        return None

    # Build schedules from 対開講 or from the current day/period
    schedules: list[Schedule] = []
    if "対開講" in notes:
        schedules = parse_paired_slots(notes, term)
    else:
        # Single slot from this row
        try:
            period = int(period_str)
            if day in VALID_DAYS and 1 <= period <= 5:
                schedules = [Schedule(term=term, day=day, period=period, room=room)]
        except (ValueError, TypeError):
            pass

    # If paired slots found, assign room to matching slot
    if schedules and room:
        # The room belongs to the current day/period slot
        for s in schedules:
            if s.day == day and (not period_str or s.period == int(period_str)):
                s.room = room
                break

    # Parse targets
    targets = parse_targets(target_raw)

    # Strip 対開講(...) from notes for storage
    clean_notes = _PAIRED_PATTERN.sub("", notes).strip()

    return ExtractedCourse(
        code=code,
        name=name,
        instructors=instructors,
        year_level=year_level,
        class_section=class_section,
        schedules=schedules,
        target_raw=target_raw,
        targets=targets,
        notes=clean_notes,
    )


def parse_intensive_row(row: list[str]) -> ExtractedCourse | None:
    """Parse a single merged intensive-table row into an ExtractedCourse.

    Intensive courses have no day/period/notes columns.
    """
    if len(row) < 7:
        return None

    code = row[_I_CODE].strip()
    if not code or not COURSE_CODE_PATTERN.match(code):
        return None

    term = row[_I_TERM].strip()
    year_class = row[_I_YEAR_CLASS].strip()
    name = row[_I_NAME].strip()
    instructor_raw = row[_I_INSTRUCTOR].strip()
    room = row[_I_ROOM].strip()
    target_raw = row[_I_TARGET].strip()

    # Parse year and class
    year_level = 1
    class_section = ""
    if year_class:
        parts = year_class.split()
        try:
            year_level = int(parts[0])
        except ValueError:
            pass
        if len(parts) > 1:
            class_section = parts[1]

    # Parse instructors
    instructors = _parse_instructors(instructor_raw)

    if term not in VALID_TERMS:
        logger.warning("Invalid term '%s' for intensive course %s, skipping", term, code)
        return None

    targets = parse_targets(target_raw)

    # Intensive courses have no schedule slots (no day/period)
    return ExtractedCourse(
        code=code,
        name=name,
        instructors=instructors,
        year_level=year_level,
        class_section=class_section,
        schedules=[],
        target_raw=target_raw,
        targets=targets,
        notes="",
    )


# ---------------------------------------------------------------------------
# Deduplication — same course appears on multiple rows (対開講)
# ---------------------------------------------------------------------------


def deduplicate_courses(
    courses: list[ExtractedCourse],
) -> list[ExtractedCourse]:
    """Merge duplicate course codes by combining their schedules.

    The PDF lists the same course once per 対開講 slot. We merge them
    into a single ExtractedCourse with all schedule slots.
    """
    by_code: dict[str, ExtractedCourse] = {}

    for course in courses:
        if course.code in by_code:
            existing = by_code[course.code]
            # Merge schedules (avoid exact duplicates)
            existing_slots = {
                (s.term, s.day, s.period) for s in existing.schedules
            }
            for s in course.schedules:
                key = (s.term, s.day, s.period)
                if key not in existing_slots:
                    existing.schedules.append(s)
                    existing_slots.add(key)
                else:
                    # Update room if the existing slot has no room
                    for es in existing.schedules:
                        if (es.term, es.day, es.period) == key and not es.room and s.room:
                            es.room = s.room
        else:
            by_code[course.code] = course

    return list(by_code.values())


# ---------------------------------------------------------------------------
# Full extraction pipeline
# ---------------------------------------------------------------------------


def extract_courses_from_pdf(
    pdf_bytes: bytes,
) -> list[ExtractedCourse]:
    """Extract all courses from a PDF timetable.

    This is the main entry point for the extraction logic.
    """
    regular_tables, intensive_tables = extract_tables_from_pdf(pdf_bytes)

    all_courses: list[ExtractedCourse] = []
    errors: list[str] = []

    # Process regular tables
    for table in regular_tables:
        merged = merge_multiline_rows(table, is_intensive=False)
        filled = carry_forward(merged, is_intensive=False)
        for row in filled:
            try:
                course = parse_regular_row(row)
                if course:
                    all_courses.append(course)
            except Exception as e:
                errors.append(f"Regular row parse error: {e} — row={row}")
                logger.warning("Failed to parse regular row: %s", e)

    # Process intensive tables
    for table in intensive_tables:
        merged = merge_multiline_rows(table, is_intensive=True)
        filled = carry_forward(merged, is_intensive=True)
        for row in filled:
            try:
                course = parse_intensive_row(row)
                if course:
                    all_courses.append(course)
            except Exception as e:
                errors.append(f"Intensive row parse error: {e} — row={row}")
                logger.warning("Failed to parse intensive row: %s", e)

    # Deduplicate (same course code from multiple 対開講 rows)
    deduped = deduplicate_courses(all_courses)

    logger.info(
        "Extracted %d courses (%d before dedup, %d errors)",
        len(deduped),
        len(all_courses),
        len(errors),
    )

    return deduped


# ---------------------------------------------------------------------------
# Download + hash
# ---------------------------------------------------------------------------


def download_pdf(url: str) -> bytes:
    """Download a PDF from a URL."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Run extraction for all pending extractions in the database."""
    from pipeline import db

    Config.validate()

    pending = db.get_pending_extractions()
    if not pending:
        logger.info("No pending extractions found")
        return

    for extraction in pending:
        extraction_id = extraction["id"]
        pdf_url = extraction["pdf_url"]
        logger.info("Processing extraction %s: %s", extraction_id, pdf_url)

        try:
            pdf_bytes = download_pdf(pdf_url)
            courses = extract_courses_from_pdf(pdf_bytes)

            # Determine academic year from URL or default to current year
            academic_year = _detect_academic_year(pdf_url)

            # Serialize courses for storage
            courses_data = [c.model_dump() for c in courses]

            # Save to database
            db.upsert_courses(courses_data, extraction_id, academic_year)
            db.update_extraction_status(
                extraction_id,
                "extracted",
                raw_json={"courses": courses_data, "count": len(courses)},
            )
            logger.info(
                "Extraction %s complete: %d courses", extraction_id, len(courses)
            )

        except Exception as e:
            logger.error("Extraction %s failed: %s", extraction_id, e)
            db.update_extraction_status(
                extraction_id,
                "pending",
                error_log=str(e),
            )


def _detect_academic_year(pdf_url: str) -> int:
    """Try to detect academic year from the PDF URL.

    URL pattern: https://www.asc.tcu.ac.jp/wp-content/uploads/YYYY/MM/{hash}.pdf
    Falls back to current calendar year.
    """
    from datetime import date

    match = re.search(r"/uploads/(\d{4})/", pdf_url)
    if match:
        return int(match.group(1))

    # Default: current year (academic year starts in April)
    today = date.today()
    return today.year


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
