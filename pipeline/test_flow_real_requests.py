import logging
import requests
import json
from bs4 import BeautifulSoup

from pipeline.config import Config
from pipeline.monitor import fetch_page, extract_pdf_links, download_pdf
from pipeline import db
from pipeline.main import (
    _handle_timetable,
    _handle_changelog,
    _handle_advance_enrollment,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def mock_update_extraction_status(
    extraction_id: str, status: str, raw_json: dict = None, error_log: str = None
):
    logger.info("Mock DB Update for %s: Status: %s", extraction_id, status)
    if raw_json:
        out_path = f"/tmp/extracted_{extraction_id}_test.json"
        with open(out_path, "w") as f:
            json.dump(raw_json, f, ensure_ascii=False, indent=2)
        logger.info("Saved DB payload to %s", out_path)


def main():
    # Bypass SUPABASE validation and intercept updates to write to local JSON
    Config.SUPABASE_URL = "http://localhost"
    Config.SUPABASE_KEY = "test"
    db.update_extraction_status = mock_update_extraction_status

    logger.info("Fetching target page: %s", Config.TARGET_URL)
    html = fetch_page(Config.TARGET_URL)

    links = extract_pdf_links(html)
    logger.info("Found %d PDF links", len(links))

    timetable_link = None
    changelog_link = None
    advance_link = None

    for link in links:
        if "変更一覧" in link.label or "変更" in link.label:
            if not changelog_link:
                changelog_link = link
        elif "先行履修" in link.label:
            if not advance_link:
                advance_link = link
        else:
            timetable_link = link

    if timetable_link:
        logger.info("--- Testing Timetable Extraction via main.py handler ---")
        logger.info("Downloading Timetable PDF: %s", timetable_link.url)
        pdf_bytes = download_pdf(timetable_link.url)

        # Use main logic directly
        _handle_timetable(
            pdf_bytes=pdf_bytes,
            pdf_url=timetable_link.url,
            extraction_id="timetable",
            semester_str=None,
            is_tentative=False,
            academic_year=2025,
        )

    if changelog_link:
        logger.info("--- Testing Changelog Extraction via main.py handler ---")
        logger.info("Downloading Changelog PDF: %s", changelog_link.url)
        pdf_bytes = download_pdf(changelog_link.url)

        # Use main logic directly
        _handle_changelog(
            pdf_bytes=pdf_bytes,
            pdf_url=changelog_link.url,
            extraction_id="changelog",
            semester_str=None,
            academic_year=2025,
        )

    if advance_link:
        logger.info("--- Testing Advance Enrollment Extraction via main.py handler ---")
        logger.info("Downloading Advance Enrollment PDF: %s", advance_link.url)
        pdf_bytes = download_pdf(advance_link.url)

        # Use main logic directly
        _handle_advance_enrollment(
            pdf_bytes=pdf_bytes,
            pdf_url=advance_link.url,
            extraction_id="advance",
            academic_year=2025,
        )


if __name__ == "__main__":
    main()
