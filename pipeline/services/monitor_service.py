from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from pipeline.models import PDFMetadata

logger = logging.getLogger(__name__)


def extract_pdf_published_at(pdf_bytes: bytes) -> str | None:
    try:
        import io
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        mod_date = reader.metadata.get("/ModDate") or reader.metadata.get("/CreationDate")
        if not mod_date:
            return None
        s = str(mod_date).strip()
        if s.startswith("D:"):
            s = s[2:]
        if len(s) >= 8:
            year, month, day = s[0:4], s[4:6], s[6:8]
            hour = s[8:10] if len(s) >= 10 else "00"
            minute = s[10:12] if len(s) >= 12 else "00"
            sec = s[12:14] if len(s) >= 14 else "00"
            tz = "+09:00"
            tz_part = s[14:] if len(s) > 14 else ""
            if "+" in tz_part or "-" in tz_part:
                sign = "+" if "+" in tz_part else "-"
                rest = tz_part.split(sign)[1].replace("'", "")
                if len(rest) == 2:
                    tz = f"{sign}{rest}:00"
                elif len(rest) >= 4:
                    tz = f"{sign}{rest[:2]}:{rest[2:4]}"
            elif "Z" in tz_part:
                tz = "+00:00"
            return f"{year}-{month}-{day}T{hour}:{minute}:{sec}{tz}"
    except Exception:
        pass
    return None


def extract_published_at(pdf_bytes: bytes, last_modified_str: str | None = None) -> str | None:
    """Extract publication timestamp in ISO 8601 format.

    Priority:
    1. HTTP Last-Modified header (if available)
    2. PDF internal metadata (/ModDate or /CreationDate)
    """
    if last_modified_str:
        return last_modified_str
    return extract_pdf_published_at(pdf_bytes)


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
        if "環境情報" in link.label or "環境情報" in link.url:
            logger.info("Skipping excluded department (環境情報): %s (%s)", link.label, link.url)
            continue

        download_result = download_pdf(link.url)
        if isinstance(download_result, tuple):
            pdf_bytes, last_modified = download_result
        else:
            pdf_bytes = download_result
            last_modified = getattr(download_result, "last_modified", None)

        pdf_hash = compute_hash(pdf_bytes)

        is_new = link.url not in stored
        is_changed = not is_new and stored[link.url].get("hash") != pdf_hash

        if not (is_new or is_changed):
            logger.debug("No change: %s", link.label)
            continue

        action = "new" if is_new else "changed"
        metadata: PDFMetadata = classify_pdf_link(link.label, url=link.url)
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
        published_at = extract_published_at(pdf_bytes, last_modified)
        create_extraction(
            link.url,
            pdf_hash,
            pdf_type=metadata.pdf_type.value,
            semester=metadata.semester.value if metadata.semester else None,
            is_tentative=metadata.is_tentative,
            academic_year=academic_year,
            published_at=published_at,
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
