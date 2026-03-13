from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, cast

from supabase import create_client, Client

from pipeline.config import Config

logger = logging.getLogger(__name__)

_client: Client | None = None

# Type alias — Supabase SDK types `data` as `JSON` (union of primitives).
# Our queries always return dicts/lists, so we cast at boundaries.
Row = dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_client() -> Client:
    global _client
    if _client is None:
        Config.validate()
        _client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    return _client


# ---------------------------------------------------------------------------
# Extractions
# ---------------------------------------------------------------------------


def create_extraction(
    pdf_url: str,
    pdf_hash: str,
    *,
    pdf_type: str = "timetable",
    semester: str = "spring",
    is_tentative: bool = False,
    academic_year: int | None = None,
    status: str = "pending",
) -> Row:
    """Create a new extraction record. Returns the inserted row."""
    payload: dict[str, Any] = {
        "pdf_url": pdf_url,
        "pdf_hash": pdf_hash,
        "pdf_type": pdf_type,
        "semester": semester,
        "is_tentative": is_tentative,
        "status": status,
    }
    if academic_year is not None:
        payload["academic_year"] = academic_year
    result = (
        get_client()
        .table("extractions")
        .insert(payload)
        .execute()
    )
    return cast(Row, result.data[0])


def update_extraction_status(
    extraction_id: str,
    status: str,
    *,
    raw_json: dict[str, Any] | None = None,
    error_log: str | None = None,
) -> Row:
    """Update an extraction's status and optional fields."""
    payload: dict[str, Any] = {"status": status, "updated_at": _now_iso()}
    if raw_json is not None:
        payload["raw_json"] = raw_json
    if error_log is not None:
        payload["error_log"] = error_log
    result = (
        get_client()
        .table("extractions")
        .update(payload)
        .eq("id", extraction_id)
        .execute()
    )
    return cast(Row, result.data[0])


def get_pending_extractions() -> list[Row]:
    """Get extractions with status='pending' (ready for LLM extraction)."""
    result = (
        get_client()
        .table("extractions")
        .select("*")
        .eq("status", "pending")
        .order("created_at")
        .execute()
    )
    return cast(list[Row], result.data)


# ---------------------------------------------------------------------------
# Courses + related tables
# ---------------------------------------------------------------------------


def upsert_courses(
    courses_data: list[dict[str, Any]],
    extraction_id: str | None = None,
    academic_year: int | None = None,
    *,
    source_type: str = "timetable",
    is_tentative: bool = False,
    semester: str | None = None,
) -> list[Row]:
    """Upsert courses and their schedules/targets.

    Each item in courses_data should match ExtractedCourse.model_dump() shape.
    Uses the course code as the unique key for upsert.

    *extraction_id* may be ``None`` for changelog-sourced courses.
    *academic_year* may be ``None``; if so, the function attempts to read
    it from the extraction record or falls back to the current year.
    Returns the upserted course rows (with generated IDs).
    """
    client = get_client()
    upserted: list[Row] = []

    if academic_year is None:
        from datetime import date

        today = date.today()
        academic_year = today.year if today.month >= 4 else today.year - 1

    for course in courses_data:
        # Upsert the course row
        course_row: dict[str, Any] = {
            "code": course["code"],
            "name": course["name"],
            "instructors": course["instructors"],
            "year_level": course.get("year_level", 1),
            "class_section": course.get("class_section", ""),
            "academic_year": academic_year,
            "notes": course.get("notes", ""),
            "source_type": source_type,
            "is_tentative": is_tentative,
        }
        if extraction_id is not None:
            course_row["extraction_id"] = extraction_id

        result = (
            client.table("courses")
            .upsert(course_row, on_conflict="code")
            .execute()
        )
        row = cast(Row, result.data[0])
        course_id: str = row["id"]

        # Delete existing schedules/targets for this course (replace on update)
        client.table("schedules").delete().eq("course_id", course_id).execute()
        client.table("course_targets").delete().eq("course_id", course_id).execute()

        # Insert schedules
        schedules = course.get("schedules", [])
        if schedules:
            schedule_rows = [
                {
                    "course_id": course_id,
                    "term": s["term"],
                    "day": s["day"],
                    "period": s["period"],
                    "room": s.get("room", ""),
                }
                for s in schedules
            ]
            client.table("schedules").insert(schedule_rows).execute()

        # Insert targets
        targets = course.get("targets", [])
        if targets:
            target_rows = [
                {
                    "course_id": course_id,
                    "target_code": t["target_code"],
                    "target_name": t["target_name"],
                    "note": t.get("note", ""),
                }
                for t in targets
            ]
            client.table("course_targets").insert(target_rows).execute()

        upserted.append(row)

    return upserted


# ---------------------------------------------------------------------------
# Course Metadata (enricher)
# ---------------------------------------------------------------------------


def upsert_metadata(
    course_id: str,
    curriculum_code: str,
    metadata: dict[str, Any],
) -> Row:
    """Upsert metadata for a course + curriculum code pair."""
    row = {
        "course_id": course_id,
        "curriculum_code": curriculum_code,
        "category": metadata.get("category"),
        "credits": metadata.get("credits"),
    }
    result = (
        get_client()
        .table("course_metadata")
        .upsert(row, on_conflict="course_id,curriculum_code")
        .execute()
    )
    return cast(Row, result.data[0])


def get_courses_needing_enrichment() -> list[Row]:
    """Get extracted courses that have no metadata row yet."""
    client = get_client()

    # Get all courses that belong to an extraction
    result = (
        client.table("courses")
        .select("id, code, name, targets:course_targets(target_code, target_name)")
        .not_.is_("extraction_id", "null")
        .execute()
    )
    courses = cast(list[Row], result.data)

    # Filter to those without any metadata
    needing: list[Row] = []
    for course in courses:
        meta_result = (
            client.table("course_metadata")
            .select("id")
            .eq("course_id", course["id"])
            .limit(1)
            .execute()
        )
        if not meta_result.data:
            needing.append(course)

    return needing


# ---------------------------------------------------------------------------
# PDF Links (monitor)
# ---------------------------------------------------------------------------


def get_stored_pdf_links() -> dict[str, Row]:
    """Get all stored PDF links, keyed by URL."""
    result = get_client().table("pdf_links").select("*").execute()
    return {cast(str, row["url"]): cast(Row, row) for row in cast(list[Row], result.data)}


def upsert_pdf_link(
    url: str, pdf_hash: str, *, label: str | None = None,
    pdf_type: str | None = None, semester: str | None = None,
) -> Row:
    """Upsert a PDF link record (for change detection)."""
    row: dict[str, Any] = {
        "url": url,
        "hash": pdf_hash,
        "updated_at": _now_iso(),
    }
    if label is not None:
        row["label"] = label
    if pdf_type is not None:
        row["pdf_type"] = pdf_type
    if semester is not None:
        row["semester"] = semester
    result = (
        get_client()
        .table("pdf_links")
        .upsert(row, on_conflict="url")
        .execute()
    )
    return cast(Row, result.data[0])


# ---------------------------------------------------------------------------
# Course queries (changelog / advance enrollment)
# ---------------------------------------------------------------------------


def delete_courses(
    *,
    academic_year: int,
    is_tentative: bool = True,
) -> int:
    """Delete tentative courses for an academic year. Returns count of deleted rows."""
    client = get_client()

    result = (
        client.table("courses")
        .select("id")
        .eq("academic_year", academic_year)
        .eq("is_tentative", is_tentative)
        .execute()
    )
    ids = [row["id"] for row in cast(list[Row], result.data)]

    if not ids:
        return 0

    for course_id in ids:
        client.table("courses").delete().eq("id", course_id).execute()

    return len(ids)


def find_course(
    *,
    code: str | None = None,
    name: str | None = None,
    term: str | None = None,
    day: str | None = None,
    period: int | str | None = None,
) -> Row | None:
    """Find a course by code (priority 1) or name+schedule composite (priority 2)."""
    client = get_client()

    # Priority 1: exact code match
    if code:
        result = client.table("courses").select("*").eq("code", code).limit(1).execute()
        if result.data:
            return cast(Row, result.data[0])

    # Priority 2: name + schedule composite
    if name:
        query = client.table("courses").select("*, schedules(term, day, period)").eq("name", name)
        result = query.execute()

        for row in cast(list[Row], result.data):
            schedules = row.get("schedules", [])
            if not term and not day and period is None:
                return cast(Row, row)
            for sched in schedules:
                match = True
                if term and sched.get("term") != term:
                    match = False
                if day and sched.get("day") != day:
                    match = False
                if period is not None and sched.get("period") != period:
                    match = False
                if match:
                    return cast(Row, row)

    return None


def update_course_fields(course_id: str, changes: list[dict[str, Any]]) -> Row:
    """Apply field-level changes to a course (and its schedules for room)."""
    payload: dict[str, Any] = {"updated_at": _now_iso()}
    field_map = {
        "担当者": "instructors",
        "科目名": "name",
        "備考": "notes",
    }
    room_value: str | None = None

    for change in changes:
        field = change.get("field", "")
        new_value = change.get("new_value")
        if field == "教室" and new_value is not None:
            room_value = new_value
            continue
        mapped = field_map.get(field)
        if mapped and new_value is not None:
            if mapped == "instructors":
                payload[mapped] = [
                    p.strip()
                    for p in new_value.replace("\n", "、").split("、")
                    if p.strip()
                ] or [new_value]
            else:
                payload[mapped] = new_value

    if room_value is not None:
        get_client().table("schedules").update({"room": room_value}).eq(
            "course_id", course_id
        ).execute()

    if len(payload) <= 1:
        result = (
            get_client().table("courses").select("*").eq("id", course_id).execute()
        )
        return cast(Row, result.data[0])

    result = (
        get_client()
        .table("courses")
        .update(payload)
        .eq("id", course_id)
        .execute()
    )
    return cast(Row, result.data[0])


def mark_cancelled(course_id: str, *, reason: str | None = None) -> Row:
    """Mark a course as cancelled."""
    payload: dict[str, Any] = {
        "status": "cancelled",
        "updated_at": _now_iso(),
    }
    if reason:
        payload["notes"] = reason
    result = (
        get_client()
        .table("courses")
        .update(payload)
        .eq("id", course_id)
        .execute()
    )
    return cast(Row, result.data[0])


def find_courses_by_name(
    name: str,
    academic_year: int,
) -> list[Row]:
    """Find courses by normalized name for advance enrollment matching."""
    import unicodedata

    normalized = unicodedata.normalize("NFKC", name).strip()

    result = (
        get_client()
        .table("courses")
        .select("*")
        .eq("academic_year", academic_year)
        .eq("status", "active")
        .execute()
    )

    matched: list[Row] = []
    for row in cast(list[Row], result.data):
        row_name = unicodedata.normalize("NFKC", row.get("name", "")).strip()
        if row_name == normalized:
            matched.append(cast(Row, row))

    return matched


def reset_advance_enrollment(academic_year: int) -> int:
    """Reset advance_enrollment flag for all courses in an academic year."""
    result = (
        get_client()
        .table("courses")
        .update({"advance_enrollment": False, "updated_at": _now_iso()})
        .eq("academic_year", academic_year)
        .eq("advance_enrollment", True)
        .execute()
    )
    return len(cast(list[Row], result.data))


def set_advance_enrollment(course_id: str) -> Row:
    """Set advance_enrollment flag on a course."""
    result = (
        get_client()
        .table("courses")
        .update({"advance_enrollment": True, "updated_at": _now_iso()})
        .eq("id", course_id)
        .execute()
    )
    return cast(Row, result.data[0])
