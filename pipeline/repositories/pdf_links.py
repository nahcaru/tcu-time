from __future__ import annotations

from typing import Any, cast

from .common import Row, first_row, get_client, now_iso


def get_stored_pdf_links() -> dict[str, Row]:
    result = get_client().table("pdf_links").select("*").execute()
    return {
        cast(str, row["url"]): cast(Row, row) for row in cast(list[Row], result.data)
    }


def upsert_pdf_link(
    url: str,
    pdf_hash: str,
    *,
    label: str | None = None,
    pdf_type: str | None = None,
    semester: str | None = None,
) -> Row:
    row: dict[str, Any] = {
        "url": url,
        "hash": pdf_hash,
        "updated_at": now_iso(),
    }
    if label is not None:
        row["label"] = label
    if pdf_type is not None:
        row["pdf_type"] = pdf_type
    if semester is not None:
        row["semester"] = semester
    result = get_client().table("pdf_links").upsert(row, on_conflict="url").execute()
    return first_row(result.data)
