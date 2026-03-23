"""Pipeline orchestrator — wires monitor and extraction into one entry point.

Design change: all handlers now save results as raw_json in the extractions
table (status='extracted') instead of writing directly to the courses table.
DB reflection happens only after admin approval via db.approve_extraction().

Intended to be invoked by GitHub Actions via::

    python -m pipeline.main
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from pipeline.config import Config
from pipeline.core.academic_year import detect_academic_year_from_url
from pipeline.extractors.advance import extract_course_names
from pipeline.extractors.changelog import parse_changelog
from pipeline.extractors.timetable import extract_courses_from_pdf
from pipeline.repositories.extractions import (
    get_pending_extractions,
    update_extraction_status,
)
from pipeline.services.extraction_service import (
    handle_advance_enrollment as _service_handle_advance_enrollment,
    handle_changelog as _service_handle_changelog,
    handle_timetable as _service_handle_timetable,
    process_extraction as _service_process_extraction,
    run_pipeline_workflow as _service_run_pipeline_workflow,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_academic_year(pdf_url: str) -> int:
    """Compatibility wrapper around the shared academic-year helper."""
    return detect_academic_year_from_url(pdf_url, today=date.today())


# ---------------------------------------------------------------------------
# Per-PDF handlers — extract only, save raw_json, await admin approval
# ---------------------------------------------------------------------------


def _handle_timetable(
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    semester_str: str | None,
    is_tentative: bool,
    academic_year: int,
) -> int:
    """Process a timetable PDF: classify → extract → save raw_json.

    Does NOT write to the courses table. Returns the number of courses extracted.
    DB reflection happens after admin approval via db.approve_extraction().
    """
    return _service_handle_timetable(
        pdf_bytes=pdf_bytes,
        pdf_url=pdf_url,
        extraction_id=extraction_id,
        semester_str=semester_str,
        is_tentative=is_tentative,
        academic_year=academic_year,
        extract_courses_from_pdf=extract_courses_from_pdf,
        update_extraction_status=update_extraction_status,
    )


def _handle_changelog(
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    semester_str: str | None,
    academic_year: int,
) -> None:
    """Process a changelog PDF: parse → save raw_json.

    Does NOT apply changes to the DB. Returns after saving raw_json.
    DB reflection happens after admin approval via db.approve_extraction().
    """
    _service_handle_changelog(
        pdf_bytes=pdf_bytes,
        pdf_url=pdf_url,
        extraction_id=extraction_id,
        semester_str=semester_str,
        academic_year=academic_year,
        parse_changelog=parse_changelog,
        update_extraction_status=update_extraction_status,
    )


def _handle_advance_enrollment(
    pdf_bytes: bytes,
    pdf_url: str,
    extraction_id: str,
    academic_year: int,
) -> None:
    """Process an advance enrollment PDF: extract names → save raw_json.

    Does NOT update advance_enrollment flags in the DB.
    DB reflection happens after admin approval via db.approve_extraction().
    """
    _service_handle_advance_enrollment(
        pdf_bytes=pdf_bytes,
        pdf_url=pdf_url,
        extraction_id=extraction_id,
        academic_year=academic_year,
        extract_course_names=extract_course_names,
        update_extraction_status=update_extraction_status,
    )


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

    _service_process_extraction(
        extraction=extraction,
        academic_year_ref=academic_year_ref,
        detect_academic_year=_detect_academic_year,
        download_pdf=download_pdf,
        handle_timetable=lambda **kwargs: _handle_timetable(
            kwargs["pdf_bytes"],
            kwargs["pdf_url"],
            kwargs["extraction_id"],
            kwargs["semester_str"],
            kwargs["is_tentative"],
            kwargs["academic_year"],
        ),
        handle_changelog=lambda **kwargs: _handle_changelog(
            kwargs["pdf_bytes"],
            kwargs["pdf_url"],
            kwargs["extraction_id"],
            kwargs["semester_str"],
            kwargs["academic_year"],
        ),
        handle_advance_enrollment=lambda **kwargs: _handle_advance_enrollment(
            kwargs["pdf_bytes"],
            kwargs["pdf_url"],
            kwargs["extraction_id"],
            kwargs["academic_year"],
        ),
        update_extraction_status=update_extraction_status,
    )


def run_pipeline() -> None:
    """Execute the pipeline: monitor → classify → extract → save raw_json.

    Does NOT write directly to the courses table. All extracted data is
    saved as raw_json in the extractions table with status='extracted'.
    Admin approval via the admin UI triggers DB reflection.
    """
    from pipeline.monitor import check_for_updates, compute_hash, download_pdf

    Config.validate()
    _service_run_pipeline_workflow(
        check_for_updates=check_for_updates,
        download_pdf=download_pdf,
        compute_hash=compute_hash,
        get_pending_extractions=get_pending_extractions,
        process_extraction=_process_extraction,
    )


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
