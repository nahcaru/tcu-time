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
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from pipeline.config import Config
from pipeline import db

logger = logging.getLogger(__name__)

# Filter string — only links whose text contains this are relevant.
GRAD_FILTER = "総合理工学研究科"


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


def extract_pdf_links(html: str, *, filter_text: str = GRAD_FILTER) -> list[PdfLink]:
    """Extract PDF links from the page HTML.

    Only links whose visible text contains *filter_text* are returned.
    Duplicate URLs are removed (keeps the first occurrence).
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[PdfLink] = []

    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        text: str = anchor.get_text(strip=True)

        # Must be a PDF link
        if not href.lower().endswith(".pdf"):
            continue

        # Must contain the filter string
        if filter_text and filter_text not in text:
            continue

        # Normalise URL (handle protocol-relative)
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            # Relative URL — should not happen on this site but be safe
            href = f"https://www.asc.tcu.ac.jp{href}"

        if href in seen:
            continue
        seen.add(href)

        links.append(PdfLink(url=href, label=text))

    logger.info("Found %d PDF link(s) matching '%s'", len(links), filter_text)
    return links


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def check_for_updates(
    target_url: str = Config.TARGET_URL,
) -> list[dict[str, str]]:
    """Check the target page for new or changed PDFs.

    Returns a list of dicts ``{"url", "label", "action"}`` describing what
    was queued.  *action* is ``"new"`` or ``"changed"``.
    """
    html = fetch_page(target_url)
    current_links = extract_pdf_links(html)

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
            logger.info(
                "[%s] %s — %s", action.upper(), link.label, link.url
            )

            # Persist the link + hash
            db.upsert_pdf_link(link.url, pdf_hash, label=link.label)

            # Queue for extraction
            db.create_extraction(link.url, pdf_hash)

            queued.append(
                {"url": link.url, "label": link.label, "action": action}
            )
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
