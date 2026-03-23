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
) -> int:
    courses = extract_courses_from_pdf(pdf_bytes)
    if not courses:
        logger.warning("No courses extracted from %s", pdf_url)
        update_extraction_status(extraction_id, "extracted", raw_json={"courses": [], "count": 0})
        return 0

    courses_data = [c.model_dump() for c in courses]
    update_extraction_status(
        extraction_id,
        "extracted",
        raw_json={
            "courses": courses_data,
            "count": len(courses),
            "semester": semester_str,
            "is_tentative": is_tentative,
            "academic_year": academic_year,
        },
    )
    logger.info(
        "Timetable extracted: %d courses from %s — awaiting admin approval",
        len(courses),
        pdf_url,
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
) -> None:
    changes = parse_changelog(pdf_bytes)
    if not changes:
        logger.info("No changelog entries found in %s", pdf_url)
        update_extraction_status(extraction_id, "extracted", raw_json={"changes": [], "count": 0})
        return

    update_extraction_status(
        extraction_id,
        "extracted",
        raw_json={
            "changes": [c.model_dump() for c in changes],
            "count": len(changes),
            "semester": semester_str or Semester.SPRING.value,
            "academic_year": academic_year,
        },
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
) -> None:
    course_names = extract_course_names(pdf_bytes)
    if not course_names:
        logger.info("No course names extracted from advance enrollment PDF %s", pdf_url)
        update_extraction_status(extraction_id, "extracted", raw_json={"names": [], "count": 0})
        return

    update_extraction_status(
        extraction_id,
        "extracted",
        raw_json={"names": course_names, "count": len(course_names), "academic_year": academic_year},
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

    try:
        if pdf_type_str == PDFType.TIMETABLE.value:
            handle_timetable(
                pdf_bytes=pdf_bytes,
                pdf_url=pdf_url,
                extraction_id=extraction_id,
                semester_str=semester_str,
                is_tentative=False,
                academic_year=year,
            )
        elif pdf_type_str == PDFType.CHANGELOG.value:
            handle_changelog(
                pdf_bytes=pdf_bytes,
                pdf_url=pdf_url,
                extraction_id=extraction_id,
                semester_str=semester_str,
                academic_year=year,
            )
        elif pdf_type_str == PDFType.ADVANCE_ENROLLMENT.value:
            handle_advance_enrollment(
                pdf_bytes=pdf_bytes,
                pdf_url=pdf_url,
                extraction_id=extraction_id,
                academic_year=year,
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
) -> None:
    """Run the monitor-driven extraction workflow."""
    new_pdfs = check_for_updates()

    academic_year_ref: list[int | None] = [None]

    if new_pdfs:
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
