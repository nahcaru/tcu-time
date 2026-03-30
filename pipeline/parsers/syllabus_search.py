"""Parser for the TCU syllabus search results page.

Parses the HTML table returned by ``slbsskgr.do`` into structured rows.
Each row contains a course code, name, target department, schedule slots,
and instructor name.

The HTML table uses 6 columns:
  No | 講義コード | 講義名 | 対象学科 | 開講期間 曜日・時限 | 担当教員

Schedule cells may contain multiple entries separated by ``<br>`` tags,
formatted as ``後期前半　火曜日　２時限`` (full-width spaces and numbers).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / mapping
# ---------------------------------------------------------------------------

TERM_MAP: dict[str, str] = {
    "後期前半": "後期前",
    "後期後半": "後期後",
    "後期": "後期",
    "前期前半": "前期前",
    "前期後半": "前期後",
    "前期": "前期",
    "通年": "通年",
    "前集中": "前集中",
    "後集中": "後集中",
}

DAY_MAP: dict[str, str] = {
    "月曜日": "月",
    "火曜日": "火",
    "水曜日": "水",
    "木曜日": "木",
    "金曜日": "金",
    "土曜日": "土",
}

# Regex for a single schedule entry: 後期前半　火曜日　２時限
_SCHEDULE_RE = re.compile(
    r"(前期前半|前期後半|前期|後期前半|後期後半|後期|通年|前集中|後集中)"
    r"\s+(\S+曜日)\s+(\d+)\s*時限"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScheduleSlot:
    """A single (term, day, period) entry."""

    term: str  # mapped term, e.g. "後期前"
    day: str  # e.g. "火"
    period: int  # e.g. 2


@dataclass
class SearchResultRow:
    """One course row from the search results table."""

    course_code: str
    course_name: str
    target_dept: str  # e.g. "26 院博前機械(機械)"
    schedules: list[ScheduleSlot] = field(default_factory=list)
    instructor: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_fullwidth(text: str) -> str:
    """Convert full-width digits/letters/spaces to half-width."""
    return unicodedata.normalize("NFKC", text)


def parse_schedule_cell(raw_text: str) -> list[ScheduleSlot]:
    """Parse a schedule cell that may contain multiple ``<br>`` entries.

    Input example (after ``get_text(separator="\\n")``)::

        後期前半　火曜日　２時限
        後期前半　水曜日　１時限

    Returns a list of :class:`ScheduleSlot` objects.
    """
    text = _normalize_fullwidth(raw_text)
    slots: list[ScheduleSlot] = []

    for match in _SCHEDULE_RE.finditer(text):
        term_text, day_text, period_text = match.groups()
        term = TERM_MAP.get(term_text, term_text)
        day = DAY_MAP.get(day_text, day_text.replace("曜日", ""))
        try:
            period = int(period_text)
        except ValueError:
            continue
        if 1 <= period <= 5:
            slots.append(ScheduleSlot(term=term, day=day, period=period))

    return slots


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_search_results(html: str) -> list[SearchResultRow]:
    """Parse the syllabus search results HTML table.

    Returns a list of :class:`SearchResultRow`, one per course found.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResultRow] = []

    # Find the results table — contains a header row with class="label"
    header_row = soup.find("tr", class_="label")
    if header_row is None:
        logger.warning("No header row (class='label') found in search results")
        return results

    table = header_row.find_parent("table")
    if table is None:
        logger.warning("Could not find parent table of header row")
        return results

    for tr in table.find_all("tr"):
        # Skip non-data rows (header, paging, utility rows)
        tr_class = tr.get("class", [])
        if not any(c.startswith("column_") for c in tr_class):
            continue

        tds = tr.find_all("td")
        if len(tds) < 6:
            continue

        # Columns: No(0), 講義コード(1), 講義名(2), 対象学科(3),
        #          開講期間 曜日・時限(4), 担当教員(5)
        no_text = _normalize_fullwidth(tds[0].get_text(strip=True))
        if not no_text.isdigit():
            continue

        code = _normalize_fullwidth(tds[1].get_text(strip=True))
        name = tds[2].get_text(strip=True)
        dept = _normalize_fullwidth(tds[3].get_text(strip=True))

        # Schedule cell may have <br> — use separator to split
        schedule_raw = tds[4].get_text(separator="\n", strip=True)
        schedules = parse_schedule_cell(schedule_raw)

        # Instructor cell may have <br> for multiple instructors
        instructor = tds[5].get_text(separator="\n", strip=True).replace("\u3000", " ")

        results.append(
            SearchResultRow(
                course_code=code,
                course_name=name,
                target_dept=dept,
                schedules=schedules,
                instructor=instructor,
            )
        )

    logger.info("Parsed %d course(s) from search results", len(results))
    return results
