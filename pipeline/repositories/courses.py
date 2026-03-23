from __future__ import annotations

from typing import Any, cast
import unicodedata

from pipeline.core.academic_year import current_academic_year

from .common import Row, first_row, get_client, now_iso


def upsert_courses(
    courses_data: list[dict[str, Any]],
    extraction_id: str | None = None,
    academic_year: int | None = None,
    *,
    source_type: str = "timetable",
    is_tentative: bool = False,
    semester: str | None = None,
) -> list[Row]:
    client = get_client()
    upserted: list[Row] = []
    academic_year = academic_year or current_academic_year()

    for course in courses_data:
        course_row: dict[str, Any] = {
            "code": course["code"],
            "name": course["name"],
            "instructors": course["instructors"],
            "year_level": course.get("year_level", 1),
            "class_section": course.get("class_section", ""),
            "academic_year": academic_year,
            "term": course.get("term", ""),
            "room": course.get("room", ""),
            "notes": course.get("notes", ""),
            "source_type": source_type,
            "is_tentative": is_tentative,
        }
        if extraction_id is not None:
            course_row["extraction_id"] = extraction_id

        result = (
            client.table("courses").upsert(course_row, on_conflict="code, academic_year").execute()
        )
        row = cast(Row, result.data[0])
        course_id: str = row["id"]

        client.table("schedules").delete().eq("course_id", course_id).execute()
        client.table("course_targets").delete().eq("course_id", course_id).execute()

        schedules = course.get("schedules", [])
        if schedules:
            schedule_rows = [
                {"course_id": course_id, "day": s["day"], "period": s["period"]}
                for s in schedules
            ]
            client.table("schedules").insert(schedule_rows).execute()

        targets = course.get("targets", [])
        if targets:
            target_rows = [
                {
                    "course_id": course_id,
                    "target_code": t["target_code"],
                    "target_name": t["target_name"],
                    "note": t.get("note", ""),
                }
                for t in targets
            ]
            client.table("course_targets").insert(target_rows).execute()

        upserted.append(row)

    return upserted


def delete_courses(*, academic_year: int, is_tentative: bool = True) -> int:
    client = get_client()
    result = (
        client.table("courses")
        .select("id")
        .eq("academic_year", academic_year)
        .eq("is_tentative", is_tentative)
        .execute()
    )
    ids = [row["id"] for row in cast(list[Row], result.data)]
    if not ids:
        return 0
    for course_id in ids:
        client.table("courses").delete().eq("id", course_id).execute()
    return len(ids)


def find_course(
    *,
    code: str | None = None,
    name: str | None = None,
    term: str | None = None,
    day: str | None = None,
    period: int | str | None = None,
) -> Row | None:
    client = get_client()
    if code:
        result = client.table("courses").select("*").eq("code", code).limit(1).execute()
        if result.data:
            return cast(Row, result.data[0])

    if name:
        result = (
            client.table("courses")
            .select("*, schedules(term, day, period)")
            .eq("name", name)
            .execute()
        )
        for row in cast(list[Row], result.data):
            schedules = row.get("schedules", [])
            if not term and not day and period is None:
                return cast(Row, row)
            for sched in schedules:
                match = True
                if term and sched.get("term") != term:
                    match = False
                if day and sched.get("day") != day:
                    match = False
                if period is not None and sched.get("period") != period:
                    match = False
                if match:
                    return cast(Row, row)
    return None


def update_course_fields(course_id: str, changes: list[dict[str, Any]]) -> Row:
    payload: dict[str, Any] = {"updated_at": now_iso()}
    field_map = {"担当者": "instructors", "科目名": "name", "備考": "notes"}
    room_value: str | None = None

    for change in changes:
        field = change.get("field", "")
        new_value = change.get("new_value")
        if field == "教室" and new_value is not None:
            room_value = new_value
            continue
        mapped = field_map.get(field)
        if mapped and new_value is not None:
            if mapped == "instructors":
                payload[mapped] = [
                    p.strip() for p in new_value.replace("\n", "、").split("、") if p.strip()
                ] or [new_value]
            else:
                payload[mapped] = new_value

    if room_value is not None:
        get_client().table("schedules").update({"room": room_value}).eq(
            "course_id", course_id
        ).execute()

    if len(payload) <= 1:
        result = get_client().table("courses").select("*").eq("id", course_id).execute()
        return first_row(result.data)

    result = get_client().table("courses").update(payload).eq("id", course_id).execute()
    return first_row(result.data)


def mark_cancelled(course_id: str, *, reason: str | None = None) -> Row:
    payload: dict[str, Any] = {"status": "cancelled", "updated_at": now_iso()}
    if reason:
        payload["notes"] = reason
    result = get_client().table("courses").update(payload).eq("id", course_id).execute()
    return first_row(result.data)


def find_courses_by_name(name: str, academic_year: int) -> list[Row]:
    normalized = unicodedata.normalize("NFKC", name).strip()
    result = (
        get_client()
        .table("courses")
        .select("*")
        .eq("academic_year", academic_year)
        .eq("status", "active")
        .execute()
    )
    matched: list[Row] = []
    for row in cast(list[Row], result.data):
        row_name = unicodedata.normalize("NFKC", row.get("name", "")).strip()
        if row_name == normalized:
            matched.append(cast(Row, row))
    return matched


def reset_advance_enrollment(academic_year: int) -> int:
    result = (
        get_client()
        .table("courses")
        .update({"advance_enrollment": False, "updated_at": now_iso()})
        .eq("academic_year", academic_year)
        .eq("advance_enrollment", True)
        .execute()
    )
    return len(cast(list[Row], result.data))


def set_advance_enrollment(course_id: str) -> Row:
    result = (
        get_client()
        .table("courses")
        .update({"advance_enrollment": True, "updated_at": now_iso()})
        .eq("id", course_id)
        .execute()
    )
    return first_row(result.data)
