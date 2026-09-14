"""Script to re-extract a specific timetable extraction record and update its raw_json."""

from __future__ import annotations

import argparse
import logging
import sys

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, ".")

from pipeline.config import Config
from pipeline.main import _handle_timetable
from pipeline.monitor import download_pdf
from pipeline.repositories.common import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def reextract_timetable(extraction_id: str = "8711ac3c-c91a-4bbe-8db8-2fa9213da88f") -> None:
    Config.validate()
    client = get_client()

    logger.info("Fetching extraction record: %s", extraction_id)
    res = client.table("extractions").select("*").eq("id", extraction_id).single().execute()
    ext = res.data
    if not ext:
        logger.error("Extraction not found: %s", extraction_id)
        return

    pdf_url = ext["pdf_url"]
    semester = ext.get("semester") or "fall"
    academic_year = ext.get("academic_year") or 2026
    is_tentative = ext.get("is_tentative") or False

    logger.info(
        "Target: %s (year=%s, semester=%s, tentative=%s)",
        pdf_url,
        academic_year,
        semester,
        is_tentative,
    )
    logger.info("Downloading PDF...")
    pdf_bytes = download_pdf(pdf_url)
    logger.info("Downloaded %d bytes. Starting extraction...", len(pdf_bytes))

    course_count = _handle_timetable(
        pdf_bytes=pdf_bytes,
        pdf_url=pdf_url,
        extraction_id=extraction_id,
        semester_str=semester,
        is_tentative=is_tentative,
        academic_year=academic_year,
    )

    logger.info("Extraction complete! Extracted %d courses.", course_count)

    # Fetch updated raw_json to inspect term distribution
    updated_res = (
        client.table("extractions")
        .select("id, status, raw_json, updated_at")
        .eq("id", extraction_id)
        .single()
        .execute()
    )
    updated_raw = updated_res.data.get("raw_json") or {}
    courses = updated_raw.get("courses", [])

    term_counts: dict[str, int] = {}
    for c in courses:
        t = c.get("term", "None")
        term_counts[t] = term_counts.get(t, 0) + 1

    logger.info("Updated status: %s", updated_res.data.get("status"))
    logger.info("Updated courses count: %d", len(courses))
    logger.info("Term distribution after re-extraction: %s", term_counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-extract a timetable extraction record")
    parser.add_argument(
        "--id",
        default="8711ac3c-c91a-4bbe-8db8-2fa9213da88f",
        help="Extraction ID",
    )
    args = parser.parse_args()
    reextract_timetable(args.id)
