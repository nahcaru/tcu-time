"""Website monitor — detects new/changed PDF timetables on the TCU page.

Fetches the target page (https://www.asc.tcu.ac.jp/6509/), extracts PDF links
for the graduate school (総合理工学研究科), and compares against stored hashes
in the ``pdf_links`` table. When a new URL or changed hash is detected, the
monitor creates an extraction record with status="pending" so the extractor
picks it up on the next run.

Scope (initial):
  - 総合理工学研究科 前期 授業時間表
  - 総合理工学研究科 後期 授業時間表
  - 授業時間表変更一覧
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterator

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from pipeline.adapters.http import fetch_bytes, fetch_text
from pipeline.config import Config
from pipeline.core.hash import compute_sha256_hex
from pipeline.models import PDFMetadata
from pipeline.parsers.monitor_page import (
    classify_pdf_link as _classify_pdf_link,
    extract_academic_year as _extract_academic_year_impl,
    extract_advance_pdf_links as _extract_advance_pdf_links,
    extract_pdf_links as _extract_pdf_links,
)
from pipeline.repositories.extractions import create_extraction
from pipeline.repositories.pdf_links import get_stored_pdf_links, upsert_pdf_link

logger = logging.getLogger(__name__)

# Structural selectors for the graduate section.
GRAD_SECTION_HEADER = "大学院"       # Text in the <h3> that marks the section
GRAD_DEPARTMENT = "総合理工学研究科"  # Text in the <h4> for our target department
ADVANCE_SECTION_HEADER = "先行履修"  # Text in the <h3> for advance enrollment


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


@dataclass
class PdfLink:
    """A PDF link found on the target page."""

    url: str
    label: str


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


def fetch_page(url: str) -> str:
    """Fetch the HTML content of the target page."""
    return fetch_text(url, timeout=30)


def download_pdf(url: str) -> bytes:
    """Download a PDF and return raw bytes."""
    return fetch_bytes(url, timeout=60)


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def _iter_siblings_until(start: Tag, stop_tags: set[str]) -> Iterator[Tag]:
    """Yield Tag siblings of *start* until a sibling whose tag name is in *stop_tags*."""
    for sibling in start.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if not isinstance(sibling, Tag):
            continue
        if sibling.name in stop_tags:
            return
        yield sibling


def extract_pdf_links(
    html: str,
    *,
    section_header: str = GRAD_SECTION_HEADER,
    department: str = GRAD_DEPARTMENT,
) -> list[PdfLink]:
    return _extract_pdf_links(
        html,
        section_header=section_header,
        department=department,
    )


def extract_advance_pdf_links(
    html: str,
    *,
    section_header: str = ADVANCE_SECTION_HEADER,
) -> list[PdfLink]:
    return _extract_advance_pdf_links(html, section_header=section_header)


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return compute_sha256_hex(data)


# ---------------------------------------------------------------------------
# PDF link classification
# ---------------------------------------------------------------------------


def classify_pdf_link(link_text: str) -> PDFMetadata:
    return _classify_pdf_link(link_text)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _extract_academic_year(soup: BeautifulSoup) -> int:
    return _extract_academic_year_impl(soup)


def check_for_updates(
    target_url: str = Config.TARGET_URL,
) -> list[dict[str, str]]:
    from pipeline.services.monitor_service import check_for_updates as _service_check_for_updates

    return _service_check_for_updates(
        target_url=target_url,
        fetch_page=fetch_page,
        extract_academic_year=_extract_academic_year,
        extract_pdf_links=extract_pdf_links,
        extract_advance_pdf_links=extract_advance_pdf_links,
        get_stored_pdf_links=get_stored_pdf_links,
        download_pdf=download_pdf,
        compute_hash=compute_hash,
        classify_pdf_link=classify_pdf_link,
        upsert_pdf_link=upsert_pdf_link,
        create_extraction=create_extraction,
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the monitor check and log results."""
    Config.validate()

    logger.info("Starting monitor check on %s", Config.TARGET_URL)
    queued = check_for_updates()

    if queued:
        logger.info(
            "Queued %d PDF(s) for extraction: %s",
            len(queued),
            ", ".join(q["label"] for q in queued),
        )
    else:
        logger.info("Monitor complete — no new extractions needed.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
