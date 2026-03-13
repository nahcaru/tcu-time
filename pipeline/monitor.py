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

import hashlib
import logging
from dataclasses import dataclass
from typing import Iterator

import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from pipeline.config import Config
from pipeline.models import PDFMetadata, PDFType, Semester
from pipeline import db

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
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def download_pdf(url: str) -> bytes:
    """Download a PDF and return raw bytes."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


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
    """Extract PDF links for *department* inside the graduate *section_header*.

    Parsing strategy (matches the live page at asc.tcu.ac.jp/6509/):
      1. Find ``div#main`` (or fall back to full document).
      2. Locate the ``<section>`` whose ``<h3>`` contains *section_header* (e.g. "大学院").
      3. Within that section, find the ``<h4>`` containing *department*.
      4. Walk siblings of that ``<h4>`` until the next ``<h4>`` or ``<hr>``.
      5. Collect all ``.pdf`` ``<a>`` links in that range.
      6. Prefix labels with the department name for downstream identification.

    Duplicate URLs are removed (keeps the first occurrence).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Step 1 — scope to main content area
    root = soup.find("div", id="main") or soup

    # Step 2 — find the graduate section
    grad_section: Tag | None = None
    for section in root.find_all("section"):
        h3 = section.find("h3")
        if h3 and section_header in h3.get_text():
            grad_section = section
            break

    if grad_section is None:
        logger.warning(
            "No <section> containing <h3> with '%s' found", section_header
        )
        return []

    # Step 3 — find the target department <h4>
    target_h4: Tag | None = None
    for h4 in grad_section.find_all("h4"):
        if department in h4.get_text():
            target_h4 = h4
            break

    if target_h4 is None:
        logger.warning(
            "No <h4> containing '%s' in graduate section", department
        )
        return []

    # Step 4 — collect elements between this <h4> and the next <h4> / <hr>
    seen: set[str] = set()
    links: list[PdfLink] = []

    for sibling in _iter_siblings_until(target_h4, {"h4", "hr"}):
        for anchor in sibling.find_all("a", href=True) if sibling.name != "a" else [sibling]:
            href = str(anchor["href"])
            text: str = anchor.get_text(strip=True)

            if not href.lower().endswith(".pdf"):
                continue

            # Normalise URL
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = f"https://www.asc.tcu.ac.jp{href}"

            if href in seen:
                continue
            seen.add(href)

            # Prefix label with department for downstream context
            label = f"〈{department}〉{text}"
            links.append(PdfLink(url=href, label=label))

    logger.info(
        "Found %d PDF link(s) for '%s' in '%s' section",
        len(links), department, section_header,
    )
    return links


def extract_advance_pdf_links(
    html: str,
    *,
    section_header: str = ADVANCE_SECTION_HEADER,
) -> list[PdfLink]:
    """Extract advance-enrollment PDF links from the 先行履修 section.

    The advance-enrollment section has no ``<h4>`` sub-structure — it's a flat
    ``<section>`` with ``<a>`` tags directly inside ``<p>`` elements.  We simply
    collect every ``.pdf`` link within the matching ``<section>``.
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("div", id="main") or soup

    # Find the advance-enrollment section
    advance_section: Tag | None = None
    for section in root.find_all("section"):
        h3 = section.find("h3")
        if h3 and section_header in h3.get_text():
            advance_section = section
            break

    if advance_section is None:
        logger.debug("No <section> containing <h3> with '%s' found", section_header)
        return []

    seen: set[str] = set()
    links: list[PdfLink] = []

    for anchor in advance_section.find_all("a", href=True):
        href = str(anchor["href"])
        text: str = anchor.get_text(strip=True)

        if not href.lower().endswith(".pdf"):
            continue

        # Normalise URL
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = f"https://www.asc.tcu.ac.jp{href}"

        if href in seen:
            continue
        seen.add(href)

        links.append(PdfLink(url=href, label=text))

    logger.info(
        "Found %d advance-enrollment PDF link(s) in '%s' section",
        len(links), section_header,
    )
    return links


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# PDF link classification
# ---------------------------------------------------------------------------


def classify_pdf_link(link_text: str) -> PDFMetadata:
    """Classify a PDF link by its text to determine type and semester.

    Pattern matching rules (from design doc):
      - "変更一覧" / "変更" → changelog
      - "先行履修"          → advance_enrollment
      - otherwise           → timetable

      - "前期"              → spring
      - "後期"              → fall
      - neither (or both)   → None (both semesters in one PDF)

    The ``is_tentative`` flag is not determinable from link text alone
    and defaults to ``False``.  The orchestrator sets it based on whether
    a confirmed fall-semester PDF has already been seen.
    """
    # Determine pdf_type
    if "変更一覧" in link_text or "変更" in link_text:
        pdf_type = PDFType.CHANGELOG
    elif "先行履修" in link_text:
        pdf_type = PDFType.ADVANCE_ENROLLMENT
    else:
        pdf_type = PDFType.TIMETABLE

    # Determine semester
    has_spring = "前期" in link_text
    has_fall = "後期" in link_text

    if has_spring and not has_fall:
        semester: Semester | None = Semester.SPRING
    elif has_fall and not has_spring:
        semester = Semester.FALL
    else:
        # Both or neither — can't determine (e.g. initial PDF with both semesters)
        semester = None

    return PDFMetadata(
        pdf_type=pdf_type,
        semester=semester,
        is_tentative=False,
    )


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def check_for_updates(
    target_url: str = Config.TARGET_URL,
) -> list[dict[str, str]]:
    """Check the target page for new or changed PDFs.

    Returns a list of dicts ``{"url", "label", "action", "pdf_type",
    "semester"}`` describing what was queued.  *action* is ``"new"`` or
    ``"changed"``.
    """
    html = fetch_page(target_url)
    current_links = extract_pdf_links(html)
    current_links.extend(extract_advance_pdf_links(html))

    if not current_links:
        logger.warning("No PDF links found on %s — page structure may have changed", target_url)
        return []

    stored = db.get_stored_pdf_links()
    queued: list[dict[str, str]] = []

    for link in current_links:
        pdf_bytes = download_pdf(link.url)
        pdf_hash = compute_hash(pdf_bytes)

        is_new = link.url not in stored
        is_changed = (
            not is_new and stored[link.url].get("hash") != pdf_hash
        )

        if is_new or is_changed:
            action = "new" if is_new else "changed"
            metadata = classify_pdf_link(link.label)
            logger.info(
                "[%s] %s — %s (type=%s, semester=%s)",
                action.upper(),
                link.label,
                link.url,
                metadata.pdf_type.value,
                metadata.semester.value if metadata.semester else "both",
            )

            # Persist the link + hash with classification metadata
            db.upsert_pdf_link(
                link.url,
                pdf_hash,
                label=link.label,
                pdf_type=metadata.pdf_type.value,
                semester=metadata.semester.value if metadata.semester else None,
            )

            # Queue for extraction with classification metadata
            db.create_extraction(
                link.url,
                pdf_hash,
                pdf_type=metadata.pdf_type.value,
                semester=metadata.semester.value if metadata.semester else "spring",
                is_tentative=metadata.is_tentative,
            )

            queued.append({
                "url": link.url,
                "label": link.label,
                "action": action,
                "pdf_type": metadata.pdf_type.value,
                "semester": metadata.semester.value if metadata.semester else "both",
            })
        else:
            logger.debug("No change: %s", link.label)

    if not queued:
        logger.info("No updates detected — all PDFs unchanged.")

    return queued


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
