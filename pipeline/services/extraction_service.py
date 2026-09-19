from __future__ import annotations

import logging
from typing import Any, Callable

from pipeline.models import PDFType, Semester

logger = logging.getLogger(__name__)


def handle_timetable(
    *,
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    semester_str: str | None,
    is_tentative: bool,
    academic_year: int,
    extract_courses_from_pdf: Callable[[bytes], list[Any]],
    update_extraction_status: Callable[..., Any],
    published_at: str | None = None,
) -> int:
    courses = extract_courses_from_pdf(pdf_bytes)
    if not courses:
        logger.warning("No courses extracted from %s", pdf_url)
        empty_raw_json: dict[str, Any] = {"courses": [], "count": 0}
        if published_at:
            empty_raw_json["published_at"] = published_at
        update_extraction_status(extraction_id, "extracted", raw_json=empty_raw_json)
        return 0

    fall_count = sum(1 for c in courses if getattr(c, "semester", None) == Semester.FALL)
    spring_count = sum(1 for c in courses if getattr(c, "semester", None) == Semester.SPRING)
    detected_semester = semester_str
    if not detected_semester:
        if fall_count > spring_count:
            detected_semester = Semester.FALL.value
        elif spring_count > fall_count:
            detected_semester = Semester.SPRING.value
    elif detected_semester == Semester.SPRING.value and fall_count > 0 and spring_count == 0:
        detected_semester = Semester.FALL.value
    elif detected_semester == Semester.FALL.value and spring_count > 0 and fall_count == 0:
        detected_semester = Semester.SPRING.value

    from pipeline.core.validator import validate_extracted_courses

    courses_data = [c.model_dump() for c in courses]
    validation_warnings = validate_extracted_courses(courses, semester=detected_semester)
    if validation_warnings:
        logger.warning(
            "Validation warnings detected for %s: %d issues found",
            pdf_url,
            len(validation_warnings),
        )

    raw_json_payload: dict[str, Any] = {
        "courses": courses_data,
        "count": len(courses),
        "semester": detected_semester,
        "is_tentative": is_tentative,
        "academic_year": academic_year,
        "validation_warnings": validation_warnings,
    }
    if published_at:
        raw_json_payload["published_at"] = published_at

    update_kwargs: dict[str, Any] = {
        "raw_json": raw_json_payload,
    }
    if detected_semester:
        update_kwargs["semester"] = detected_semester

    update_extraction_status(
        extraction_id,
        "extracted",
        **update_kwargs,
    )
    logger.info(
        "Timetable extracted: %d courses from %s (semester=%s) — awaiting admin approval",
        len(courses),
        pdf_url,
        detected_semester,
    )
    return len(courses)


def handle_changelog(
    *,
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    semester_str: str | None,
    academic_year: int,
    parse_changelog: Callable[[bytes], list[Any]],
    update_extraction_status: Callable[..., Any],
    published_at: str | None = None,
) -> None:
    changes = parse_changelog(pdf_bytes)
    if not changes:
        logger.info("No changelog entries found in %s", pdf_url)
        empty_raw_json: dict[str, Any] = {"changes": [], "count": 0}
        if published_at:
            empty_raw_json["published_at"] = published_at
        update_extraction_status(extraction_id, "extracted", raw_json=empty_raw_json)
        return

    raw_json_payload: dict[str, Any] = {
        "changes": [c.model_dump() for c in changes],
        "count": len(changes),
        "semester": semester_str or Semester.SPRING.value,
        "academic_year": academic_year,
    }
    if published_at:
        raw_json_payload["published_at"] = published_at

    update_extraction_status(
        extraction_id,
        "extracted",
        raw_json=raw_json_payload,
    )
    logger.info(
        "Changelog extracted: %d entries from %s — awaiting admin approval",
        len(changes),
        pdf_url,
    )


def handle_advance_enrollment(
    *,
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    academic_year: int,
    extract_course_names: Callable[[bytes], list[str]],
    update_extraction_status: Callable[..., Any],
    published_at: str | None = None,
) -> None:
    course_names = extract_course_names(pdf_bytes)
    if not course_names:
        logger.info("No course names extracted from advance enrollment PDF %s", pdf_url)
        empty_raw_json: dict[str, Any] = {"names": [], "count": 0}
        if published_at:
            empty_raw_json["published_at"] = published_at
        update_extraction_status(extraction_id, "extracted", raw_json=empty_raw_json)
        return

    raw_json_payload: dict[str, Any] = {
        "names": course_names,
        "count": len(course_names),
        "academic_year": academic_year,
    }
    if published_at:
        raw_json_payload["published_at"] = published_at

    update_extraction_status(
        extraction_id,
        "extracted",
        raw_json=raw_json_payload,
    )
    logger.info(
        "Advance enrollment extracted: %d names from %s — awaiting admin approval",
        len(course_names),
        pdf_url,
    )


def process_extraction(
    *,
    extraction: dict[str, Any],
    academic_year_ref: list[int | None],
    detect_academic_year: Callable[[str], int],
    download_pdf: Callable[[str], bytes],
    handle_timetable: Callable[..., int],
    handle_changelog: Callable[..., None],
    handle_advance_enrollment: Callable[..., None],
    update_extraction_status: Callable[..., Any],
) -> None:
    pdf_url: str = extraction["pdf_url"]
    pdf_type_str: str = extraction.get("pdf_type", "timetable")
    semester_str: str | None = extraction.get("semester")
    extraction_id: str = extraction["id"]

    if semester_str == "both":
        semester_str = None

    try:
        pdf_bytes = download_pdf(pdf_url)
    except Exception:
        logger.error("Failed to download %s", pdf_url, exc_info=True)
        return

    year = detect_academic_year(pdf_url)
    if academic_year_ref[0] is None:
        academic_year_ref[0] = year

    raw_json_data = extraction.get("raw_json")
    published_at = raw_json_data.get("published_at") if isinstance(raw_json_data, dict) else None
    if not published_at:
        from pipeline.services.monitor_service import extract_published_at

        last_modified = getattr(pdf_bytes, "last_modified", None)
        published_at = extract_published_at(pdf_bytes, last_modified)

    try:
        if pdf_type_str == PDFType.TIMETABLE.value:
            handle_timetable(
                pdf_bytes=pdf_bytes,
                pdf_url=pdf_url,
                extraction_id=extraction_id,
                semester_str=semester_str,
                is_tentative=False,
                academic_year=year,
                published_at=published_at,
            )
        elif pdf_type_str == PDFType.CHANGELOG.value:
            handle_changelog(
                pdf_bytes=pdf_bytes,
                pdf_url=pdf_url,
                extraction_id=extraction_id,
                semester_str=semester_str,
                academic_year=year,
                published_at=published_at,
            )
        elif pdf_type_str == PDFType.ADVANCE_ENROLLMENT.value:
            handle_advance_enrollment(
                pdf_bytes=pdf_bytes,
                pdf_url=pdf_url,
                extraction_id=extraction_id,
                academic_year=year,
                published_at=published_at,
            )
        else:
            logger.warning("Unknown pdf_type '%s' for %s — skipping", pdf_type_str, pdf_url)
            return
    except Exception:
        logger.error("Processing failed for %s", pdf_url, exc_info=True)
        update_extraction_status(
            extraction_id,
            "pending",
            error_log="Processing failed: see logs",
        )


def run_pipeline_workflow(
    *,
    check_for_updates: Callable[[], list[dict[str, Any]]],
    download_pdf: Callable[[str], bytes],
    compute_hash: Callable[[bytes], str],
    get_pending_extractions: Callable[[], list[dict[str, Any]]],
    process_extraction: Callable[[dict[str, Any], list[int | None]], None],
    notify_new_pdfs: Callable[[list[dict[str, Any]]], Any] | None = None,
) -> None:
    """Run the monitor-driven extraction workflow."""
    new_pdfs = check_for_updates()

    academic_year_ref: list[int | None] = [None]

    if new_pdfs:
        if notify_new_pdfs is not None:
            try:
                notify_new_pdfs(new_pdfs)
            except Exception:
                logger.warning("Failed to send notification for new PDFs", exc_info=True)
        else:
            try:
                from pipeline.services.github_issue_service import (
                    create_github_issue_for_new_pdfs,
                )

                create_github_issue_for_new_pdfs(new_pdfs)
            except Exception:
                logger.warning("Failed to create GitHub issue for new PDFs", exc_info=True)

        logger.info("Processing %d new/changed PDF(s)", len(new_pdfs))
        for pdf_info in new_pdfs:
            pdf_url: str = pdf_info["url"]
            try:
                pdf_bytes = download_pdf(pdf_url)
            except Exception:
                logger.error("Failed to download %s", pdf_url, exc_info=True)
                continue

            pdf_hash = compute_hash(pdf_bytes)
            pending = get_pending_extractions()
            extraction_id: str | None = None
            for ext in pending:
                if ext["pdf_url"] == pdf_url and ext["pdf_hash"] == pdf_hash:
                    extraction_id = ext["id"]
                    break

            if extraction_id is None:
                logger.warning("No pending extraction record found for %s — skipping", pdf_url)
                continue

            process_extraction(
                {**pdf_info, "id": extraction_id, "pdf_url": pdf_url},
                academic_year_ref,
            )

    remaining_pending = get_pending_extractions()
    if remaining_pending:
        logger.info("Retrying %d pending extraction(s)", len(remaining_pending))
        for ext in remaining_pending:
            process_extraction(ext, academic_year_ref)

    if not new_pdfs and not remaining_pending:
        logger.info("No updates detected — pipeline finished.")
        return

    logger.info("Pipeline run complete. Extracted data awaiting admin approval.")
