"""Syllabus enricher — scrapes TCU syllabus pages for metadata.

For each extracted course, fetches the syllabus HTML and extracts:
- category (分野系列): e.g. "授業科目", "共通科目"
- credits (単位数): e.g. 2.0

Grad school syllabi don't require a curriculum code parameter, unlike
undergrad which needs crclumcd. The enricher stores one metadata row
per course with curriculum_code="default".
"""

from __future__ import annotations

import logging
import time

import requests

from pipeline.adapters.http import (
    LegacyTLSAdapter,
    create_legacy_tls_session,
    fetch_syllabus_html,
)
from pipeline.core.academic_year import current_academic_year
from pipeline.parsers.syllabus import (
    SyllabusFields,
    find_label_value as _find_label_value,
    parse_syllabus_html,
)
from pipeline.models import CourseMetadata
from pipeline.repositories.common import Row
from pipeline.repositories.metadata import (
    get_courses_needing_enrichment,
    upsert_metadata,
)

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "TCU-TIME Syllabus Enricher/1.0 (grad timetable pipeline)",
}


class _LegacyTLSAdapter(LegacyTLSAdapter):
    """HTTPS adapter that lowers the SSL security level for legacy servers.

    websrv.tcu.ac.jp rejects modern TLS handshakes with
    TLSV1_ALERT_INSUFFICIENT_SECURITY.  Lowering the security level to 1
    and adding legacy renegotiation lets us connect.
    """


def _get_session() -> requests.Session:
    session = create_legacy_tls_session(headers=_HEADERS)
    session.mount("https://websrv.tcu.ac.jp", _LegacyTLSAdapter())
    return session


_session: requests.Session | None = None


def _get_shared_session() -> requests.Session:
    global _session
    if _session is None:
        _session = _get_session()
    return _session


# Default curriculum code for grad school (no per-curriculum variation).
DEFAULT_CURRICULUM_CODE = "default"


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------


def build_syllabus_url(
    year: int,
    course_code: str,
) -> str:
    from pipeline.services.enrichment_service import build_syllabus_url as _service_build_syllabus_url

    return _service_build_syllabus_url(year, course_code)


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------


def fetch_syllabus_page(url: str) -> str | None:
    """Fetch syllabus HTML. Returns *None* on any HTTP / network error."""
    return fetch_syllabus_html(_get_shared_session(), url, timeout=30)


# ---------------------------------------------------------------------------
# High-level scraping
# ---------------------------------------------------------------------------


def scrape_syllabus(
    year: int,
    course_code: str,
) -> CourseMetadata | None:
    from pipeline.services.enrichment_service import scrape_syllabus as _service_scrape_syllabus

    return _service_scrape_syllabus(
        year,
        course_code,
        fetch_syllabus_page=fetch_syllabus_page,
        build_syllabus_url=build_syllabus_url,
        parse_syllabus_html=parse_syllabus_html,
    )


def enrich_courses(
    courses: list[Row],
    academic_year: int,
) -> tuple[int, int]:
    from pipeline.services.enrichment_service import enrich_courses as _service_enrich_courses

    return _service_enrich_courses(
        courses,
        academic_year,
        scrape_syllabus=scrape_syllabus,
        sleep=time.sleep,
        upsert_metadata=upsert_metadata,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _detect_academic_year() -> int:
    """Compatibility wrapper around the shared academic-year helper."""
    return current_academic_year()


def main() -> None:
    """Enrich all courses that have no metadata yet."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting syllabus enricher")

    courses = get_courses_needing_enrichment()
    if not courses:
        logger.info("No courses need enrichment — nothing to do")
        return

    academic_year = _detect_academic_year()
    logger.info(
        "Enriching %d courses for academic year %d",
        len(courses),
        academic_year,
    )

    success, failure = enrich_courses(courses, academic_year)
    logger.info(
        "Enrichment complete: %d succeeded, %d failed (of %d total)",
        success,
        failure,
        len(courses),
    )

    if failure > 0:
        logger.warning(
            "%d courses failed enrichment — re-run to retry", failure
        )


if __name__ == "__main__":
    main()
