from __future__ import annotations

import json
import logging
from io import BytesIO

import pdfplumber
from google import genai

from pipeline.config import Config
from pipeline.models import ChangeEntry, FieldChange
from pipeline import db

logger = logging.getLogger(__name__)


def _extract_all_text(pdf_bytes: bytes) -> str:
    pages_text: list[str] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text() or "")
    return "\n\n".join(pages_text).strip()


def _parse_gemini_json(raw_text: str) -> list[ChangeEntry]:
    payload = json.loads(raw_text.strip())

    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if "change_type" in payload:
            items = [payload]
        elif isinstance(payload.get("entries"), list):
            items = payload["entries"]
        else:
            raise ValueError("Unexpected JSON structure from Gemini")
    else:
        raise ValueError("Gemini response is not JSON object/array")

    entries: list[ChangeEntry] = []
    for item in items:
        entry = ChangeEntry.model_validate(item)
        entry.changes = [FieldChange.model_validate(change) for change in entry.changes]
        entries.append(entry)
    return entries


def _generate_changes_with_model(client: genai.Client, model: str, all_text: str) -> list[ChangeEntry]:
    prompt = f"""
以下は東京都市大学の授業時間表の変更一覧です。
各変更エントリを JSON として出力してください。

出力スキーマ:
{{
  "change_type": "add | modify | cancel",
  "course_code": "講義コード (あれば)",
  "course_name": "科目名",
  "term": "学期",
  "day": "曜日",
  "period": "時限 (整数 or '集中')",
  "changes": [
    {{
      "field": "変更対象フィールド",
      "old_value": "変更前の値 (あれば)",
      "new_value": "変更後の値"
    }}
  ],
  "reason": "変更理由 (あれば)"
}}

変更一覧テキスト:
{all_text}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return _parse_gemini_json(response.text or "")


def parse_changelog(pdf_bytes: bytes) -> list[ChangeEntry]:
    all_text = _extract_all_text(pdf_bytes)
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

    try:
        return _generate_changes_with_model(client, Config.GEMINI_MODEL, all_text)
    except Exception as primary_error:
        logger.warning(
            "Primary Gemini model failed for changelog parsing: %s. Falling back to %s",
            primary_error,
            Config.GEMINI_FALLBACK_MODEL,
        )
        return _generate_changes_with_model(client, Config.GEMINI_FALLBACK_MODEL, all_text)


def _entry_to_course_upsert_payload(entry: ChangeEntry, semester: str) -> dict[str, object]:
    name = entry.course_name
    code = entry.course_code
    notes = entry.reason or ""
    instructors: list[str] = ["未定"]

    for change in entry.changes:
        if change.field in ("科目名", "name") and change.new_value:
            name = change.new_value
        elif change.field in ("講義コード", "code") and change.new_value:
            code = change.new_value
        elif change.field in ("備考", "notes") and change.new_value:
            notes = change.new_value
        elif change.field in ("担当者", "instructors") and change.new_value:
            instructors = [part.strip() for part in change.new_value.replace("\n", "、").split("、") if part.strip()] or [change.new_value]

    schedule: list[dict[str, object]] = []
    if entry.term and entry.day and isinstance(entry.period, int):
        room = ""
        for change in entry.changes:
            if change.field in ("教室", "room") and change.new_value:
                room = change.new_value
                break
        schedule = [{"term": entry.term, "day": entry.day, "period": entry.period, "room": room}]

    return {
        "code": code,
        "name": name,
        "instructors": instructors,
        "year_level": 1,
        "class_section": "",
        "semester": semester,
        "schedules": schedule,
        "target_raw": "",
        "targets": [],
        "notes": notes,
        "source_type": "changelog",
    }


def _find_course_for_change(entry: ChangeEntry) -> db.Row | None:
    if entry.course_code:
        course = db.find_course(code=entry.course_code)
        if course:
            return course

    if entry.course_name and entry.term and entry.day and isinstance(entry.period, int):
        course = db.find_course(
            name=entry.course_name,
            term=entry.term,
            day=entry.day,
            period=entry.period,
        )
        if course:
            return course

    if entry.course_name and entry.term:
        result = (
            db.get_client()
            .table("courses")
            .select("*, schedules(term, day, period)")
            .eq("name", entry.course_name)
            .execute()
        )
        candidates: list[db.Row] = []
        for row in result.data:
            schedules = row.get("schedules", [])
            if any(s.get("term") == entry.term for s in schedules):
                candidates.append(row)

        if len(candidates) > 1:
            logger.warning(
                "Multiple courses matched by name+term for '%s' (%s): %d",
                entry.course_name,
                entry.term,
                len(candidates),
            )
        if candidates:
            return candidates[0]

    return None


def apply_changelog(
    changes: list[ChangeEntry],
    semester: str,
    academic_year: int | None = None,
) -> None:
    added = 0
    modified = 0
    cancelled = 0

    for entry in changes:
        if entry.change_type == "add":
            payload = _entry_to_course_upsert_payload(entry, semester)
            if not payload.get("code"):
                logger.warning("Add change skipped due to missing course_code: %s", entry.course_name)
                continue
            db.upsert_courses(
                [payload],
                academic_year=academic_year,
                source_type="changelog",
                semester=semester,
            )
            added += 1
            continue

        course = _find_course_for_change(entry)
        if not course:
            logger.warning(
                "No course matched changelog entry: type=%s code=%s name=%s term=%s day=%s period=%s",
                entry.change_type,
                entry.course_code,
                entry.course_name,
                entry.term,
                entry.day,
                entry.period,
            )
            continue

        course_id = course["id"]

        if entry.change_type == "modify":
            db.update_course_fields(course_id, [c.model_dump() for c in entry.changes])
            modified += 1
        elif entry.change_type == "cancel":
            db.mark_cancelled(course_id, reason=entry.reason)
            cancelled += 1

    logger.info(
        "Changelog applied: %d added, %d modified, %d cancelled",
        added,
        modified,
        cancelled,
    )
