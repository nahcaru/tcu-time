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
import re
import time
from dataclasses import dataclass

import ssl

import requests
import urllib3
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from pipeline.config import Config
from pipeline import db
from pipeline.models import CourseMetadata

logger = logging.getLogger(__name__)

# Suppress only the InsecureRequestWarning from urllib3 (TLS verify=False).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_HEADERS = {
    "User-Agent": "TCU-TIME Syllabus Enricher/1.0 (grad timetable pipeline)",
}


class _LegacyTLSAdapter(HTTPAdapter):
    """HTTPS adapter that lowers the SSL security level for legacy servers.

    websrv.tcu.ac.jp rejects modern TLS handshakes with
    TLSV1_ALERT_INSUFFICIENT_SECURITY.  Lowering the security level to 1
    and adding legacy renegotiation lets us connect.
    """

    def init_poolmanager(self, *args, **kwargs):  # type: ignore[override]
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _get_session() -> requests.Session:
    s = requests.Session()
    s.mount("https://websrv.tcu.ac.jp", _LegacyTLSAdapter())
    s.headers.update(_HEADERS)
    return s


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
    """Build a syllabus detail page URL.

    For grad school, no curriculum code is needed — the server
    returns the syllabus without it.
    """
    base = Config.SYLLABUS_BASE_URL.rstrip("/")
    params = (
        f"value(risyunen)={year}"
        f"&value(semekikn)=1"
        f"&value(kougicd)={course_code}"
    )
    return f"{base}/slbssbdr.do?{params}"


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------


def fetch_syllabus_page(url: str) -> str | None:
    """Fetch syllabus HTML. Returns *None* on any HTTP / network error."""
    try:
        resp = _get_shared_session().get(
            url,
            verify=False,  # noqa: S501 — TLS cert issues on websrv.tcu.ac.jp
            timeout=30,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except requests.RequestException:
        logger.warning("Failed to fetch syllabus: %s", url, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


@dataclass
class SyllabusFields:
    """Parsed fields from a syllabus detail page."""

    category: str | None = None
    credits: float | None = None


def _find_label_value(
    rows: list[Tag],
    label_substr: str,
) -> str | None:
    """Find the value cell adjacent to a label cell containing *label_substr*.

    The syllabus HTML uses ``<td class="label_kougi">`` for labels and
    ``<td class="kougi">`` for values. This is robust across undergrad /
    grad layouts where row indices differ.
    """
    for tr in rows:
        label_td = tr.find("td", class_="label_kougi")
        if label_td and label_substr in label_td.get_text():
            value_td = tr.find("td", class_="kougi")
            if value_td:
                # Strip &nbsp; and whitespace
                return value_td.get_text(strip=True).replace("\xa0", "")
    return None


# Pattern: ■category■ or [category・compulsoriness]
_GRAD_CATEGORY_RE = re.compile(r"■(.+?)■")
_UNDERGRAD_CATEGORY_RE = re.compile(r"\[(.+?)・(.+?)\]")


def parse_syllabus_html(html: str) -> SyllabusFields:
    """Parse a syllabus HTML page and extract metadata fields.

    Handles both grad-school format (``■授業科目■``) and undergrad format
    (``[専門・選択]``).
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="syllabus_detail")
    if table is None:
        logger.warning("No syllabus_detail table found in HTML")
        return SyllabusFields()

    rows = table.find_all("tr")  # type: ignore[union-attr]
    fields = SyllabusFields()

    # --- Credits (単位数) ---
    credits_text = _find_label_value(rows, "単位数")
    if credits_text:
        try:
            fields.credits = float(credits_text)
        except ValueError:
            logger.warning("Could not parse credits: %r", credits_text)

    # --- Category (分野系列) ---
    category_text = _find_label_value(rows, "分野系列")
    if category_text:
        # Try grad-school format first: ■授業科目■
        grad_match = _GRAD_CATEGORY_RE.search(category_text)
        if grad_match:
            fields.category = grad_match.group(1)
        else:
            # Try undergrad format: [専門・選択]
            undergrad_match = _UNDERGRAD_CATEGORY_RE.search(category_text)
            if undergrad_match:
                fields.category = undergrad_match.group(1)
            else:
                # Fallback: use raw text as category
                fields.category = category_text if category_text else None

    return fields


# ---------------------------------------------------------------------------
# High-level scraping
# ---------------------------------------------------------------------------


def scrape_syllabus(
    year: int,
    course_code: str,
) -> CourseMetadata | None:
    """Scrape a single syllabus page and return parsed metadata.

    Returns *None* if the page cannot be fetched or parsed.
    """
    url = build_syllabus_url(year, course_code)
    html = fetch_syllabus_page(url)
    if html is None:
        return None

    fields = parse_syllabus_html(html)
    return CourseMetadata(
        curriculum_code=DEFAULT_CURRICULUM_CODE,
        category=fields.category,
        credits=fields.credits,
    )


def enrich_courses(
    courses: list[db.Row],
    academic_year: int,
) -> tuple[int, int]:
    """Enrich a list of courses with syllabus metadata.

    Args:
        courses: Rows from ``get_courses_needing_enrichment()``, each
            having at minimum ``id``, ``code``, and ``targets``.
        academic_year: The academic year for syllabus lookups (e.g. 2025).

    Returns:
        (success_count, failure_count) tuple.
    """
    if not courses:
        return 0, 0

    success = 0
    failure = 0

    for i, course in enumerate(courses):
        course_id: str = course["id"]
        course_code: str = course["code"]
        course_name: str = course.get("name", course_code)

        logger.info(
            "[%d/%d] Enriching %s (%s)",
            i + 1,
            len(courses),
            course_name,
            course_code,
        )

        if i > 0:
            time.sleep(Config.SCRAPE_DELAY_SEC)

        meta = scrape_syllabus(academic_year, course_code)
        if meta is None:
            logger.warning(
                "Failed to scrape syllabus for %s",
                course_code,
            )
            failure += 1
            continue

        try:
            db.upsert_metadata(
                course_id=course_id,
                curriculum_code=meta.curriculum_code,
                metadata={
                    "category": meta.category,
                    "credits": meta.credits,
                },
            )
            success += 1
        except Exception:
            logger.error(
                "DB upsert failed for %s",
                course_code,
                exc_info=True,
            )
            failure += 1

    return success, failure


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _detect_academic_year() -> int:
    """Best-effort academic year detection (same logic as extractor)."""
    from datetime import date

    today = date.today()
    # Japanese academic year starts in April.
    return today.year if today.month >= 4 else today.year - 1


def main() -> None:
    """Enrich all courses that have no metadata yet."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting syllabus enricher")

    courses = db.get_courses_needing_enrichment()
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
