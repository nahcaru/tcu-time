from __future__ import annotations

import logging
from typing import Any

from pipeline.core.academic_year import current_academic_year
from pipeline.models import ChangeEntry
from pipeline.repositories import courses, extractions

logger = logging.getLogger(__name__)

Row = dict[str, Any]


def _apply_timetable_approval(extraction: Row) -> int:
    raw = extraction.get("raw_json") or {}
    courses_data: list[dict[str, Any]] = raw.get("courses", [])
    if not courses_data:
        return 0

    semester = raw.get("semester")
    is_tentative: bool = bool(raw.get("is_tentative", False))
    academic_year: int | None = raw.get("academic_year")

    if semester == "fall" and not is_tentative and academic_year is not None:
        deleted = courses.delete_courses(academic_year=academic_year, is_tentative=True)
        if deleted:
            logger.info(
                "Deleted %d tentative fall courses before reflecting approved data",
                deleted,
            )

    upserted = courses.upsert_courses(
        courses_data,
        extraction_id=extraction["id"],
        academic_year=academic_year,
        source_type="timetable",
        is_tentative=is_tentative,
        semester=semester,
    )
    return len(upserted)


def _apply_changelog_approval(extraction: Row) -> int:
    raw = extraction.get("raw_json") or {}
    changes_data: list[dict[str, Any]] = raw.get("changes", [])
    if not changes_data:
        return 0

    academic_year: int | None = raw.get("academic_year")
    changes = [ChangeEntry.model_validate(c) for c in changes_data]

    for change in changes:
        if change.change_type == "create":
            if not change.course_name or not change.course_code:
                continue
            courses.upsert_courses(
                [
                    {
                        "code": change.course_code,
                        "name": change.course_name,
                        "instructors": ["未定"],
                        "source_type": "changelog",
                        "notes": "",
                        "schedules": [],
                        "targets": [],
                    }
                ],
                extraction_id=extraction["id"],
                academic_year=academic_year,
                source_type="changelog",
            )
            continue

        course = courses.find_course(
            code=change.course_code,
            name=change.course_name,
            term=change.term,
            day=change.day,
            period=change.period,
        )
        if not course:
            logger.warning(
                "%s: course not found: %s / %s",
                change.change_type,
                change.course_code,
                change.course_name,
            )
            continue

        if change.change_type == "update":
            field_changes = [c.model_dump() for c in change.changes]
            courses.update_course_fields(course["id"], field_changes)
        elif change.change_type == "delete":
            courses.mark_cancelled(course["id"])

    return len(changes)


def _apply_advance_approval(extraction: Row) -> int:
    raw = extraction.get("raw_json") or {}
    names: list[str] = raw.get("names", [])
    if not names:
        return 0

    academic_year = raw.get("academic_year") or current_academic_year()
    courses.reset_advance_enrollment(academic_year)

    count = 0
    for name in names:
        matched = courses.find_courses_by_name(name, academic_year)
        for course in matched:
            courses.set_advance_enrollment(course["id"])
            count += 1

    return count


def approve_extraction(extraction_id: str) -> int:
    extraction = extractions.get_extraction_detail(extraction_id)
    if extraction is None:
        raise ValueError(f"Extraction not found: {extraction_id}")

    pdf_type: str = extraction.get("pdf_type", "timetable")
    try:
        if pdf_type == "timetable":
            count = _apply_timetable_approval(extraction)
        elif pdf_type == "changelog":
            count = _apply_changelog_approval(extraction)
        elif pdf_type == "advance_enrollment":
            count = _apply_advance_approval(extraction)
        else:
            raise ValueError(f"Unknown pdf_type: {pdf_type}")
    except Exception:
        logger.error("Approval failed for extraction %s", extraction_id, exc_info=True)
        raise

    extractions.update_extraction_status(extraction_id, "approved")
    logger.info(
        "Approved extraction %s (%s): %d records affected",
        extraction_id,
        pdf_type,
        count,
    )
    return count
