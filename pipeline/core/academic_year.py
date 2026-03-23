from __future__ import annotations

from datetime import date
import re


def current_academic_year(today: date | None = None) -> int:
    """Return the Japanese academic year, which starts in April."""
    current = today or date.today()
    return current.year if current.month >= 4 else current.year - 1


def detect_academic_year_from_url(pdf_url: str, today: date | None = None) -> int:
    """Best-effort academic year detection from a PDF URL."""
    match = re.search(r"/uploads/(\d{4})/", pdf_url)
    if match:
        return int(match.group(1))
    return current_academic_year(today)
