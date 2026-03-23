from __future__ import annotations

from typing import Any, cast

from .common import Row, first_row, get_client, now_iso


def create_extraction(
    pdf_url: str,
    pdf_hash: str,
    *,
    pdf_type: str = "timetable",
    semester: str = "spring",
    is_tentative: bool = False,
    academic_year: int | None = None,
    status: str = "pending",
) -> Row:
    payload: dict[str, Any] = {
        "pdf_url": pdf_url,
        "pdf_hash": pdf_hash,
        "pdf_type": pdf_type,
        "semester": semester,
        "is_tentative": is_tentative,
        "status": status,
    }
    if academic_year is not None:
        payload["academic_year"] = academic_year
    result = get_client().table("extractions").insert(payload).execute()
    return first_row(result.data)


def update_extraction_status(
    extraction_id: str,
    status: str,
    *,
    raw_json: dict[str, Any] | None = None,
    error_log: str | None = None,
) -> Row:
    payload: dict[str, Any] = {"status": status, "updated_at": now_iso()}
    if raw_json is not None:
        payload["raw_json"] = raw_json
    if error_log is not None:
        payload["error_log"] = error_log
    result = (
        get_client().table("extractions").update(payload).eq("id", extraction_id).execute()
    )
    return first_row(result.data)


def get_pending_extractions() -> list[Row]:
    result = (
        get_client()
        .table("extractions")
        .select("*")
        .eq("status", "pending")
        .order("created_at")
        .execute()
    )
    return cast(list[Row], result.data)


def get_extractions_for_review(*, status: str = "extracted", limit: int = 50) -> list[Row]:
    result = (
        get_client()
        .table("extractions")
        .select(
            "id, pdf_url, pdf_type, semester, is_tentative, academic_year, status, created_at, updated_at"
        )
        .eq("status", status)
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return cast(list[Row], result.data)


def get_extraction_detail(extraction_id: str) -> Row | None:
    result = (
        get_client().table("extractions").select("*").eq("id", extraction_id).single().execute()
    )
    if not result.data:
        return None
    return cast(Row, result.data)
