"""Pipeline orchestrator — wires monitor, classifier, extractor, changelog,
advance enrollment, and enricher into a single ``run_pipeline()`` entry point.

Intended to be invoked by GitHub Actions via::

    python -m pipeline.main
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from pipeline import db
from pipeline.config import Config
from pipeline.models import PDFType, Semester

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_academic_year(pdf_url: str) -> int:
    """Try to detect academic year from a PDF URL.

    URL pattern: ``https://…/uploads/YYYY/MM/{hash}.pdf``
    Falls back to the current Japanese academic year (starts in April).
    """
    match = re.search(r"/uploads/(\d{4})/", pdf_url)
    if match:
        return int(match.group(1))

    today = date.today()
    return today.year if today.month >= 4 else today.year - 1


# ---------------------------------------------------------------------------
# Per-PDF dispatch
# ---------------------------------------------------------------------------


def _handle_timetable(
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    semester_str: str | None,
    is_tentative: bool,
    academic_year: int,
) -> int:
    """Process a timetable PDF: classify → extract → upsert courses.

    Returns the number of courses upserted.
    """
    from pipeline.classifier import classify_pages
    from pipeline.extractor import extract_courses_from_pdf

    classifications = classify_pages(pdf_bytes)
    courses = extract_courses_from_pdf(pdf_bytes, classifications)

    if not courses:
        logger.warning("No courses extracted from %s", pdf_url)
        db.update_extraction_status(extraction_id, "extracted", raw_json={"courses": [], "count": 0})
        return 0

    # When a confirmed fall PDF arrives, delete tentative fall data first.
    if not is_tentative and semester_str == Semester.FALL.value:
        deleted = db.delete_courses(academic_year=academic_year, is_tentative=True)
        if deleted:
            logger.info("Deleted %d tentative fall courses before inserting confirmed data", deleted)

    courses_data = [c.model_dump() for c in courses]

    db.upsert_courses(
        courses_data,
        extraction_id=extraction_id,
        academic_year=academic_year,
        source_type="timetable",
        is_tentative=is_tentative,
        semester=semester_str,
    )
    db.update_extraction_status(
        extraction_id,
        "extracted",
        raw_json={"courses": courses_data, "count": len(courses)},
    )
    logger.info("Timetable extraction complete: %d courses from %s", len(courses), pdf_url)
    return len(courses)


def _handle_changelog(
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    semester_str: str | None,
    academic_year: int,
) -> None:
    """Process a changelog PDF: parse → apply diffs."""
    from pipeline.changelog import apply_changelog, parse_changelog

    changes = parse_changelog(pdf_bytes)
    if not changes:
        logger.info("No changelog entries found in %s", pdf_url)
        db.update_extraction_status(extraction_id, "extracted", raw_json={"changes": [], "count": 0})
        return

    apply_changelog(
        changes,
        semester=semester_str or Semester.SPRING.value,
        academic_year=academic_year,
    )
    db.update_extraction_status(
        extraction_id,
        "extracted",
        raw_json={"changes": [c.model_dump() for c in changes], "count": len(changes)},
    )
    logger.info("Changelog applied: %d entries from %s", len(changes), pdf_url)


def _handle_advance_enrollment(
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    academic_year: int,
) -> None:
    """Process an advance enrollment PDF: extract names → update flags."""
    from pipeline.advance import extract_course_names, update_flags

    course_names = extract_course_names(pdf_bytes)
    if not course_names:
        logger.info("No course names extracted from advance enrollment PDF %s", pdf_url)
        db.update_extraction_status(extraction_id, "extracted", raw_json={"names": [], "count": 0})
        return

    update_flags(course_names, academic_year)
    db.update_extraction_status(
        extraction_id,
        "extracted",
        raw_json={"names": course_names, "count": len(course_names)},
    )
    logger.info("Advance enrollment flags updated: %d names from %s", len(course_names), pdf_url)


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------


def _run_enrichment(academic_year: int) -> None:
    """Run syllabus enrichment for courses missing metadata."""
    from pipeline.enricher import enrich_courses

    courses = db.get_courses_needing_enrichment()
    if not courses:
        logger.info("No courses need enrichment")
        return

    logger.info("Enriching %d courses for academic year %d", len(courses), academic_year)
    success, failure = enrich_courses(courses, academic_year)
    logger.info("Enrichment complete: %d succeeded, %d failed", success, failure)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def _process_extraction(
    extraction: dict[str, Any],
    academic_year_ref: list[int | None],
) -> None:
    """Download PDF and dispatch to the appropriate handler.

    *academic_year_ref* is a single-element list used as a mutable reference so
    the caller can track the detected academic year across multiple invocations.
    """
    from pipeline.monitor import download_pdf

    pdf_url: str = extraction["pdf_url"]
    pdf_type_str: str = extraction.get("pdf_type", "timetable")
    semester_str: str | None = extraction.get("semester")
    extraction_id: str = extraction["id"]

    if semester_str == "both":
        semester_str = None

    # Download PDF
    try:
        pdf_bytes = download_pdf(pdf_url)
    except Exception:
        logger.error("Failed to download %s", pdf_url, exc_info=True)
        return

    year = _detect_academic_year(pdf_url)
    if academic_year_ref[0] is None:
        academic_year_ref[0] = year

    # Determine tentative flag.
    is_tentative = False

    try:
        if pdf_type_str == PDFType.TIMETABLE.value:
            _ = _handle_timetable(
                pdf_bytes,
                pdf_url,
                extraction_id,
                semester_str,
                is_tentative,
                year,
            )

        elif pdf_type_str == PDFType.CHANGELOG.value:
            _handle_changelog(
                pdf_bytes,
                pdf_url,
                extraction_id,
                semester_str,
                year,
            )

        elif pdf_type_str == PDFType.ADVANCE_ENROLLMENT.value:
            _handle_advance_enrollment(
                pdf_bytes,
                pdf_url,
                extraction_id,
                year,
            )

        else:
            logger.warning("Unknown pdf_type '%s' for %s — skipping", pdf_type_str, pdf_url)
            return

    except Exception:
        logger.error("Processing failed for %s", pdf_url, exc_info=True)
        db.update_extraction_status(
            extraction_id,
            "pending",
            error_log="Processing failed: see logs",
        )


def run_pipeline() -> None:
    """Execute the full pipeline: monitor → classify → extract/diff → enrich."""
    from pipeline.monitor import check_for_updates, compute_hash, download_pdf

    Config.validate()

    # Step 1: Monitor for new/changed PDFs
    new_pdfs = check_for_updates()

    academic_year_ref: list[int | None] = [None]

    # Step 1a: Process newly detected PDFs.
    if new_pdfs:
        logger.info("Processing %d new/changed PDF(s)", len(new_pdfs))
        for pdf_info in new_pdfs:
            pdf_url: str = pdf_info["url"]
            # Download to match extraction record by URL + hash.
            try:
                pdf_bytes = download_pdf(pdf_url)
            except Exception:
                logger.error("Failed to download %s", pdf_url, exc_info=True)
                continue

            pdf_hash = compute_hash(pdf_bytes)
            pending = db.get_pending_extractions()
            extraction_id: str | None = None
            for ext in pending:
                if ext["pdf_url"] == pdf_url and ext["pdf_hash"] == pdf_hash:
                    extraction_id = ext["id"]
                    break

            if extraction_id is None:
                logger.warning("No pending extraction record found for %s — skipping", pdf_url)
                continue

            _process_extraction(
                {**pdf_info, "id": extraction_id, "pdf_url": pdf_url},
                academic_year_ref,
            )

    # Step 1b: Retry any remaining pending extractions (e.g. previous failures).
    remaining_pending = db.get_pending_extractions()
    if remaining_pending:
        logger.info("Retrying %d pending extraction(s)", len(remaining_pending))
        for ext in remaining_pending:
            _process_extraction(ext, academic_year_ref)

    if not new_pdfs and not remaining_pending:
        logger.info("No updates detected — pipeline finished.")
        return

    # Step 2: Enrichment
    if academic_year_ref[0] is not None:
        _run_enrichment(academic_year_ref[0])

    logger.info("Pipeline run complete.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry: ``python -m pipeline.main``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_pipeline()


if __name__ == "__main__":
    main()
