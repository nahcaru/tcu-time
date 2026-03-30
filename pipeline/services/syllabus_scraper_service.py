"""Syllabus search scraper service.

Scrapes fall-semester course data from the TCU syllabus search site
(``websrv.tcu.ac.jp/tcu_web_v3/slbsskgr.do``) and upserts directly into
the courses, schedules, course_targets, and course_metadata tables.

This is a *temporary* data source used when fall-semester timetable PDFs
are not yet available.  Once the PDFs are published and processed through
the normal pipeline, these records can be superseded.

.. note::
   The syllabus search server requires a JSESSIONID cookie from an initial
   GET request, and the actual search uses a POST request.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from pipeline.adapters.http import create_legacy_tls_session
from pipeline.core.settings import Settings
from pipeline.parsers.syllabus import parse_syllabus_html
from pipeline.parsers.syllabus_search import (
    SearchResultRow,
    parse_search_results,
)
from pipeline.repositories.courses import upsert_courses
from pipeline.repositories.metadata import upsert_metadata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Curriculum definitions
# ---------------------------------------------------------------------------

# Maps curriculum code -> option label from the search form.
CURRICULA: dict[str, str] = {
    "sm260101": "26 院博前機械(機械)",
    "sm260201": "26 院博前機械(機シ)",
    "sm260301": "26 院博前電気・化学(電気)",
    "sm260401": "26 院博前電気・化学(医用)",
    "sm260501": "26 院博前電気・化学(応化)",
    "sm260601": "26 院博前共同(共同)",
    "sm260602": "26 院博前共同(共同・早)",
    "sm260701": "26 院博前建築都市デザイン(建築)",
    "sm260801": "26 院博前建築都市デザイン(都市)",
    "sm260901": "26 院博前情報(情報)",
    "sm261001": "26 院博前情報(シ情)",
    "sm261101": "26 院博前自然(自然)",
}

# Maps kaikoCd -> descriptive label for logging.
KAIKO_CODES: dict[str, str] = {
    "04": "後期",
    "05": "後期前",
    "06": "後期後",
    "09": "後集中",
}

# Regex to extract target_name from option labels like "26 院博前機械(機械)".
_TARGET_NAME_RE = re.compile(r"院博前(.+?)\(")

# Syllabus search form endpoint.
_SEARCH_ENDPOINT = "/slbsskgr.do"
# Syllabus detail endpoint.
_DETAIL_ENDPOINT = "/slbssbdr.do"


# ---------------------------------------------------------------------------
# Target extraction
# ---------------------------------------------------------------------------


@dataclass
class TargetInfo:
    """Target department info derived from a curriculum code + label."""

    target_code: str  # e.g. "01"
    target_name: str  # e.g. "機械"
    note: str = ""  # e.g. "機シ"  (text inside parentheses)


def extract_target(crclm: str, label: str) -> TargetInfo:
    """Derive target_code and target_name from a curriculum code and label.

    - ``target_code``: digits at positions [-4:-2] of the curriculum code
    - ``target_name``: text between "院博前" and "(" in the label
    """
    target_code = crclm[-4:-2]

    name_match = _TARGET_NAME_RE.search(label)
    target_name = name_match.group(1) if name_match else label

    # Extract note from parentheses, e.g. "(機械)" → "機械"
    paren_match = re.search(r"\((.+?)\)", label)
    note = paren_match.group(1) if paren_match else ""

    return TargetInfo(target_code=target_code, target_name=target_name, note=note)


# ---------------------------------------------------------------------------
# Accumulated course data (across multiple curriculum searches)
# ---------------------------------------------------------------------------


@dataclass
class AccumulatedCourse:
    """Course data accumulated across multiple curriculum search results."""

    code: str
    name: str
    instructors: list[str]
    term: str  # primary term (from first schedule slot)
    room: str = ""
    schedules: list[dict[str, Any]] = field(default_factory=list)
    targets: list[dict[str, str]] = field(default_factory=list)
    notes: str = ""
    # Enrichment data (from detail page)
    credits: float | None = None
    category: str | None = None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _init_session() -> requests.Session:
    """Create a TLS session and establish a JSESSIONID cookie."""
    session = create_legacy_tls_session()
    base = Settings.SYLLABUS_BASE_URL.rstrip("/")
    form_url = f"{base}{_SEARCH_ENDPOINT}"
    try:
        r = session.get(form_url, verify=False, timeout=30)
        r.raise_for_status()
        logger.info("Session established (JSESSIONID acquired)")
    except requests.RequestException:
        logger.warning("Failed to initialise session cookie", exc_info=True)
    return session


def _fetch_search_results(
    session: requests.Session,
    year: int,
    crclm: str,
    kaiko_cd: str,
) -> str | None:
    """Submit a POST search and return the HTML response."""
    base = Settings.SYLLABUS_BASE_URL.rstrip("/")
    url = f"{base}{_SEARCH_ENDPOINT}"
    data = {
        "value(methodname)": "sylkougi_search",
        "buttonName": "searchKougi",
        "value(nendo)": str(year),
        "value(campuscd)": "",
        "value(crclm)": crclm,
        "tagakb": "off",
        "value(bunya)": "",
        "value(grade)": "",
        "value(kouginm)": "",
        "value(syokunm)": "",
        "value(kaikoCd)": kaiko_cd,
    }
    try:
        r = session.post(url, data=data, verify=False, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text
    except requests.RequestException:
        logger.warning("POST search failed for %s / %s", crclm, kaiko_cd, exc_info=True)
        return None


def _fetch_detail_page(
    session: requests.Session,
    year: int,
    course_code: str,
    crclm: str = "",
) -> str | None:
    """Fetch the syllabus detail page for a given course."""
    base = Settings.SYLLABUS_BASE_URL.rstrip("/")
    url = (
        f"{base}{_DETAIL_ENDPOINT}?"
        f"value(risyunen)={year}"
        f"&value(semekikn)=1"
        f"&value(kougicd)={course_code}"
    )
    if crclm:
        url += f"&value(crclumcd)={crclm}"
    try:
        r = session.get(url, verify=False, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text
    except requests.RequestException:
        logger.warning("Failed to fetch detail page for %s", course_code, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Row → internal model helpers
# ---------------------------------------------------------------------------


def _row_to_instructors(row: SearchResultRow) -> list[str]:
    """Split instructor text into a list of individual names."""
    raw = row.instructor.strip()
    if not raw:
        return ["未定"]
    parts = re.split(r"[、,\n]", raw)
    return [p.strip() for p in parts if p.strip()] or [raw]


def _row_to_schedules(row: SearchResultRow) -> list[dict[str, Any]]:
    """Convert schedule slots into dicts suitable for DB insertion."""
    return [{"day": s.day, "period": s.period} for s in row.schedules]


def _primary_term(row: SearchResultRow) -> str:
    """Get the primary term from schedule slots."""
    if row.schedules:
        return row.schedules[0].term
    return ""


# ---------------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------------


def scrape_all_courses(
    year: int,
    *,
    curricula: dict[str, str] | None = None,
    kaiko_codes: dict[str, str] | None = None,
    delay: float = Settings.SCRAPE_DELAY_SEC,
    dry_run: bool = False,
) -> list[AccumulatedCourse]:
    """Scrape course data from all curriculum × term combinations.

    Returns a deduplicated list of :class:`AccumulatedCourse` objects,
    with targets merged from multiple curricula.
    """
    curricula = curricula or CURRICULA
    kaiko_codes = kaiko_codes or KAIKO_CODES

    session = _init_session()

    # dict: course_code → AccumulatedCourse
    courses_by_code: dict[str, AccumulatedCourse] = {}
    # dict: course_code → set of target_codes already added
    seen_targets: dict[str, set[str]] = {}
    # dict: course_code → first crclm that found it (for detail page)
    first_crclm: dict[str, str] = {}

    total_combos = len(curricula) * len(kaiko_codes)
    combo_index = 0

    for crclm, label in curricula.items():
        target_info = extract_target(crclm, label)

        for kaiko_cd, kaiko_label in kaiko_codes.items():
            combo_index += 1
            logger.info(
                "[%d/%d] Fetching %s / %s ...",
                combo_index,
                total_combos,
                label,
                kaiko_label,
            )

            if combo_index > 1:
                time.sleep(delay)

            html = _fetch_search_results(session, year, crclm, kaiko_cd)
            if html is None:
                continue

            rows = parse_search_results(html)
            logger.info("  → %d course(s) found", len(rows))

            for row in rows:
                code = row.course_code

                if code not in courses_by_code:
                    courses_by_code[code] = AccumulatedCourse(
                        code=code,
                        name=row.course_name,
                        instructors=_row_to_instructors(row),
                        term=_primary_term(row),
                        schedules=_row_to_schedules(row),
                    )
                    seen_targets[code] = set()
                    first_crclm[code] = crclm

                # Add target if not already present for this course
                if target_info.target_code not in seen_targets[code]:
                    courses_by_code[code].targets.append(
                        {
                            "target_code": target_info.target_code,
                            "target_name": target_info.target_name,
                            "note": target_info.note,
                        }
                    )
                    seen_targets[code].add(target_info.target_code)

    logger.info(
        "Search complete: %d unique course(s) found", len(courses_by_code)
    )

    # Second pass: fetch detail pages for credits/category.
    courses = list(courses_by_code.values())
    if not dry_run:
        _enrich_from_detail_pages(session, courses, year, first_crclm, delay)

    return courses


def _enrich_from_detail_pages(
    session: requests.Session,
    courses: list[AccumulatedCourse],
    year: int,
    first_crclm: dict[str, str],
    delay: float,
) -> None:
    """Fetch syllabus detail pages and extract credits/category."""
    for i, course in enumerate(courses):
        if i > 0:
            time.sleep(delay)

        crclm = first_crclm.get(course.code, "")
        logger.info(
            "[%d/%d] Enriching %s (%s) ...",
            i + 1,
            len(courses),
            course.name,
            course.code,
        )

        html = _fetch_detail_page(session, year, course.code, crclm)
        if html is None:
            logger.warning("Failed to fetch detail page for %s", course.code)
            continue

        fields = parse_syllabus_html(html)
        course.credits = fields.credits
        course.category = fields.category

    enriched = sum(1 for c in courses if c.credits is not None)
    logger.info("Enriched %d / %d courses from detail pages", enriched, len(courses))


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------


def persist_courses(
    courses: list[AccumulatedCourse],
    academic_year: int,
) -> tuple[int, int]:
    """Upsert courses and metadata into the database.

    Returns (courses_upserted, metadata_upserted).
    """
    course_dicts = [
        {
            "code": c.code,
            "name": c.name,
            "instructors": c.instructors,
            "year_level": 1,
            "class_section": "",
            "term": c.term,
            "room": c.room,
            "schedules": c.schedules,
            "targets": c.targets,
            "notes": c.notes,
        }
        for c in courses
    ]

    upserted_rows = upsert_courses(
        course_dicts,
        extraction_id=None,
        academic_year=academic_year,
        source_type="syllabus",
        is_tentative=False,
    )

    # Upsert metadata for each course that has enrichment data.
    meta_count = 0
    for row, acc in zip(upserted_rows, courses):
        if acc.credits is not None or acc.category is not None:
            upsert_metadata(
                course_id=row["id"],
                curriculum_code="default",
                metadata={"category": acc.category, "credits": acc.credits},
            )
            meta_count += 1

    return len(upserted_rows), meta_count
