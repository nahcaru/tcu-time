from __future__ import annotations

from typing import Any, cast

from .common import Row, first_row, get_client


def upsert_metadata(course_id: str, curriculum_code: str, metadata: dict[str, Any]) -> Row:
    row = {
        "course_id": course_id,
        "curriculum_code": curriculum_code,
        "category": metadata.get("category"),
        "credits": metadata.get("credits"),
    }
    result = (
        get_client()
        .table("course_metadata")
        .upsert(row, on_conflict="course_id,curriculum_code")
        .execute()
    )
    return first_row(result.data)


def get_courses_needing_enrichment() -> list[Row]:
    client = get_client()
    result = (
        client.table("courses")
        .select("id, code, name, targets:course_targets(target_code, target_name)")
        .not_.is_("extraction_id", "null")
        .execute()
    )
    courses = cast(list[Row], result.data)

    needing: list[Row] = []
    for course in courses:
        meta_result = (
            client.table("course_metadata")
            .select("id")
            .eq("course_id", course["id"])
            .limit(1)
            .execute()
        )
        if not meta_result.data:
            needing.append(course)

    return needing
