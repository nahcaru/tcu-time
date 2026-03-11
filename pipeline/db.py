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
    pdf_url: str, pdf_hash: str, *, status: str = "pending"
) -> Row:
    """Create a new extraction record. Returns the inserted row."""
    result = (
        get_client()
        .table("extractions")
        .insert({"pdf_url": pdf_url, "pdf_hash": pdf_hash, "status": status})
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
    extraction_id: str,
    academic_year: int,
) -> list[Row]:
    """Upsert courses and their schedules/targets.

    Each item in courses_data should match ExtractedCourse.model_dump() shape.
    Uses the course code as the unique key for upsert.
    Returns the upserted course rows (with generated IDs).
    """
    client = get_client()
    upserted: list[Row] = []

    for course in courses_data:
        # Upsert the course row
        course_row = {
            "code": course["code"],
            "name": course["name"],
            "instructors": course["instructors"],
            "year_level": course.get("year_level", 1),
            "class_section": course.get("class_section", ""),
            "academic_year": academic_year,
            "notes": course.get("notes", ""),
            "extraction_id": extraction_id,
        }
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
        "compulsoriness": metadata.get("compulsoriness"),
        "credits": metadata.get("credits"),
        "syllabus_url": metadata.get("syllabus_url"),
    }
    result = (
        get_client()
        .table("course_metadata")
        .upsert(row, on_conflict="course_id,curriculum_code")
        .execute()
    )
    return cast(Row, result.data[0])


def get_courses_needing_enrichment() -> list[Row]:
    """Get extracted courses with targets and existing metadata codes."""
    client = get_client()

    # Get all courses that belong to an extraction
    result = (
        client.table("courses")
        .select("id, code, name, targets:course_targets(target_code, target_name)")
        .not_.is_("extraction_id", "null")
        .execute()
    )
    courses = cast(list[Row], result.data)

    for course in courses:
        meta_result = (
            client.table("course_metadata")
            .select("curriculum_code")
            .eq("course_id", course["id"])
            .execute()
        )
        course["existing_metadata_codes"] = [
            cast(str, r["curriculum_code"]) for r in cast(list[Row], meta_result.data)
        ]

    return courses


# ---------------------------------------------------------------------------
# PDF Links (monitor)
# ---------------------------------------------------------------------------


def get_stored_pdf_links() -> dict[str, Row]:
    """Get all stored PDF links, keyed by URL."""
    result = get_client().table("pdf_links").select("*").execute()
    return {cast(str, row["url"]): cast(Row, row) for row in cast(list[Row], result.data)}


def upsert_pdf_link(
    url: str, pdf_hash: str, *, label: str | None = None
) -> Row:
    """Upsert a PDF link record (for change detection)."""
    row: dict[str, Any] = {
        "url": url,
        "hash": pdf_hash,
        "updated_at": _now_iso(),
    }
    if label is not None:
        row["label"] = label
    result = (
        get_client()
        .table("pdf_links")
        .upsert(row, on_conflict="url")
        .execute()
    )
    return cast(Row, result.data[0])
