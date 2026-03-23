from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from pipeline.models import PDFMetadata

logger = logging.getLogger(__name__)


def check_for_updates(
    *,
    target_url: str,
    fetch_page,
    extract_academic_year,
    extract_pdf_links,
    extract_advance_pdf_links,
    get_stored_pdf_links,
    download_pdf,
    compute_hash,
    classify_pdf_link,
    upsert_pdf_link,
    create_extraction,
) -> list[dict[str, str]]:
    html = fetch_page(target_url)
    soup = BeautifulSoup(html, "html.parser")
    academic_year = extract_academic_year(soup)

    current_links = extract_pdf_links(html)
    current_links.extend(extract_advance_pdf_links(html))

    if not current_links:
        logger.warning("No PDF links found on %s — page structure may have changed", target_url)
        return []

    stored = get_stored_pdf_links()
    queued: list[dict[str, str]] = []

    for link in current_links:
        pdf_bytes = download_pdf(link.url)
        pdf_hash = compute_hash(pdf_bytes)

        is_new = link.url not in stored
        is_changed = not is_new and stored[link.url].get("hash") != pdf_hash

        if not (is_new or is_changed):
            logger.debug("No change: %s", link.label)
            continue

        action = "new" if is_new else "changed"
        metadata: PDFMetadata = classify_pdf_link(link.label)
        logger.info(
            "[%s] %s — %s (type=%s, semester=%s)",
            action.upper(),
            link.label,
            link.url,
            metadata.pdf_type.value,
            metadata.semester.value if metadata.semester else "both",
        )

        upsert_pdf_link(
            link.url,
            pdf_hash,
            label=link.label,
            pdf_type=metadata.pdf_type.value,
            semester=metadata.semester.value if metadata.semester else None,
        )
        create_extraction(
            link.url,
            pdf_hash,
            pdf_type=metadata.pdf_type.value,
            semester=metadata.semester.value if metadata.semester else "spring",
            is_tentative=metadata.is_tentative,
            academic_year=academic_year,
        )
        queued.append(
            {
                "url": link.url,
                "label": link.label,
                "action": action,
                "pdf_type": metadata.pdf_type.value,
                "semester": metadata.semester.value if metadata.semester else "both",
            }
        )

    if not queued:
        logger.info("No updates detected — all PDFs unchanged.")

    return queued
