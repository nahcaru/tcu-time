from __future__ import annotations

import io
import logging
import re
import unicodedata
from typing import Any

import pdfplumber
from pydantic import BaseModel, Field

from pipeline.adapters.gemini import (
    create_client,
    generate_pdf_json,
    run_with_model_fallback,
)
from pipeline.core.settings import Settings
from pipeline.models import ChangeEntry, CourseTarget, FieldChange, Schedule

logger = logging.getLogger(__name__)

REQUIRED_HEADER_KEYWORDS = ("科目名", "講義名")
POSSIBLE_HEADER_KEYWORDS = (
    "変更",
    "開講",
    "クラス",
    "曜日時限",
    "曜日",
    "時限",
    "学期",
    "学年",
    "講義コード",
    "時間割コード",
    "科目コード",
    "教室",
    "受講対象",
    "再履修",
    "備考",
    "担当者",
    "教員",
)

GEMINI_CHANGELOG_PROMPT = """
あなたは東京都市大学の時間割変更一覧（PDF）から変更差分を正確に抽出する専門AIです。
このPDFは横向き（landscape）の密な表形式で、各セル内に「旧値 \n → 新値」の形式で変更が記載されています。

以下の仕様に厳密に従って、変更エントリを JSON 形式で抽出してください：

1. 各行の判定と change_type（厳密に "create", "update", "delete" のいずれか）：
   - 【削除 (delete)】: セルに「→（削除）」または「（削除）」が複数含まれる行。
     * change_type は必ず "delete" とする。（"cancel", "modify", "remove" は絶対に使用禁止）
     * changes 配列は空配列 [] とする。
     * course_code, course_name, term, day, period には「→（削除）」を除いた変更前の旧値を設定する。
   - 【新規 (create)】: セルに「（新規）」が含まれる行。
     * change_type は必ず "create" とする。（"add", "insert", "new" は絶対に使用禁止）
     * changes 配列は空配列 [] とする。
     * course_code, course_name, term, day, period には「（新規）」「→」を除いた新講義の値を設定する。
   - 【更新 (update)】: 各セルに「→」が含まれる行。
     * change_type は必ず "update" とする。（"modify", "change" は絶対に使用禁止）
     * 講義を特定するため、course_code, course_name, term, day, period には変更前の旧値（未変更ならその値）を設定する。
     * changes 配列に、変更があった各セルについて FieldChange (field=列名, old_value=変更前, new_value=変更後) を格納する。

2. フィールド抽出とテキスト整形：
   - 教室名: セル内で改行されて「12N \n → 共用演習室」となっている場合、old_value は "12N", new_value は "共用演習室" です。数値を勝手に分割したり（"1" と "2N" など）しないでください。
   - 講義コード: "smab030111" や "smaz030191" などの文字列から、0や英数字を絶対に省略・欠落させないでください。
   - 改行の除去: セル内の単語途中の改行（\n）は除去して結合してください（例: "Sustainable Cyber-\nPhysical Systems" → "Sustainable Cyber-Physical Systems"）。
   - 列名: changes 内の field には「教室」「担当者」「曜日時限」などの表の列名をそのまま設定してください。
"""


class ChangelogResponse(BaseModel):
    entries: list[ChangeEntry] = Field(
        description="List of changelog items extracted from text"
    )


def clean_text(s: str | None) -> str:
    """Normalize text, fix wrapped words across newlines, and trim whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).strip()
    s = re.sub(r"-\s*\n\s*", "-", s)
    s = re.sub(r"([a-zA-Z0-9])\s*\n\s*([a-zA-Z0-9])", r"\1 \2", s)
    s = re.sub(r"\s*\n\s*", "", s)
    return s.strip()


def parse_schedules(
    text: str | None,
) -> tuple[str | None, int | str | None, list[Schedule]]:
    """Parse day of week (月-土) and period (1-5 or 集中) from schedule cell.

    Supports multiple day/period slots (e.g. "火1,金1", "水1,水2", "月5,木5").
    Returns (summary_day, primary_period, list_of_schedules).
    """
    if not text:
        return None, None, []
    t = clean_text(text)
    if "集中" in t:
        return None, "集中", []

    matches = re.findall(r"([月火水木金土])\s*([1-5])", t)
    schedules: list[Schedule] = []
    seen: set[tuple[str, int]] = set()
    for d, p in matches:
        pair = (d, int(p))
        if pair not in seen:
            seen.add(pair)
            schedules.append(Schedule(day=d, period=int(p)))

    if schedules:
        unique_days = list(dict.fromkeys(s.day for s in schedules))
        days = ",".join(unique_days)
        return days, schedules[0].period, schedules

    m = re.search(r"([月火水木金土])", t)
    if m:
        return m.group(1), None, []

    return None, None, []


def parse_day_period(text: str | None) -> tuple[str | None, int | str | None]:
    """Backward-compatible helper returning (first_day, first_period)."""
    d, p, scheds = parse_schedules(text)
    if scheds:
        return scheds[0].day, scheds[0].period
    return d, p


def parse_target_str(s: str) -> CourseTarget:
    """Parse target string into code, name, and note."""
    s = s.strip()
    if not s:
        return CourseTarget(target_code="", target_name="", note="")
    note = ""
    m_note = re.search(r"^(.*?)[（(]([^）)]+)[）)]\s*$", s)
    if m_note:
        s = m_note.group(1).strip()
        note = m_note.group(2).strip()
    m_code = re.match(r"^([0-9]{1,2}[A-Za-z]?|[A-Za-z0-9]+)[\s:：\-・]*(.*)$", s)
    if m_code and re.match(r"^\d", m_code.group(1)):
        return CourseTarget(
            target_code=m_code.group(1),
            target_name=m_code.group(2) or "",
            note=note,
        )
    return CourseTarget(target_code="", target_name=s, note=note)


def _detect_headers(row: list[str | None]) -> list[str] | None:
    """Detect if row matches TCU changelog headers and return canonical names."""
    if not row:
        return None
    cleaned = [re.sub(r"\s+", "", str(c or "")) for c in row]
    has_name_col = any(any(kw in c for kw in REQUIRED_HEADER_KEYWORDS) for c in cleaned)
    if not has_name_col:
        return None
    matched_count = sum(
        1 for c in cleaned if any(kw in c for kw in POSSIBLE_HEADER_KEYWORDS)
    )
    if matched_count < 3:
        return None

    headers: list[str] = []
    for i, c in enumerate(cleaned):
        if "再履修" in c:
            headers.append("再履修者科目名")
        elif "科目名" in c or "講義名" in c:
            headers.append("科目名")
        elif "講義コード" in c or "時間割コード" in c or "科目コード" in c:
            headers.append("講義コード")
        elif ("曜日" in c and "時限" in c) or c == "曜日時限":
            headers.append("曜日時限")
        elif "学期" in c:
            headers.append("学期")
        elif "学年" in c:
            headers.append("学年")
        elif "教室" in c:
            headers.append("教室")
        elif "担当者" in c or "教員" in c:
            headers.append("担当者")
        elif "受講対象" in c or "対象" in c:
            headers.append("受講対象")
        elif "備考" in c:
            headers.append("備考")
        elif "開講" in c:
            headers.append("開講")
        elif "クラス" in c:
            headers.append("クラス")
        elif "変更" in c:
            headers.append("変更")
        else:
            headers.append(c or f"col_{i}")
    return headers


def _parse_table_row(
    row: list[str | None], headers: list[str]
) -> ChangeEntry | None:
    """Parse a single table row into a ChangeEntry."""
    if not row or not any(row):
        return None

    row_dict: dict[str, str] = {}
    for idx, col in enumerate(headers):
        val = str(row[idx] or "") if idx < len(row) else ""
        row_dict[col] = val

    del_count = sum(1 for v in row if v and ("（削除）" in v or "(削除)" in v))
    has_new = any(v and ("（新規）" in v or "(新規)" in v) for v in row)
    has_arrow = any(v and ("→" in v or "->" in v) for v in row)

    if del_count >= 2:
        # Deletions
        def strip_del(s: str) -> str:
            cleaned = re.sub(r"→?\s*[（\(]削除[）\)]", "", s)
            return clean_text(cleaned)

        code = strip_del(row_dict.get("講義コード", ""))
        name = strip_del(row_dict.get("科目名", ""))
        term = strip_del(row_dict.get("学期", ""))
        sched_raw = strip_del(row_dict.get("曜日時限", ""))
        day, period, scheds = parse_schedules(sched_raw)

        if not name and not code:
            return None

        return ChangeEntry(
            change_type="delete",
            course_code=code or None,
            course_name=name,
            term=term or None,
            day=day,
            period=period,
            schedules=scheds,
            changes=[],
        )

    elif has_new:
        # Creations
        def strip_new(s: str) -> str:
            cleaned = re.sub(r"^[（\(]新規[）\)]\s*→?\s*", "", s)
            return clean_text(cleaned)

        code = strip_new(row_dict.get("講義コード", ""))
        name = strip_new(row_dict.get("科目名", ""))
        term = strip_new(row_dict.get("学期", ""))
        sched_raw = strip_new(row_dict.get("曜日時限", ""))
        day, period, scheds = parse_schedules(sched_raw)
        room = strip_new(row_dict.get("教室", ""))
        instr_raw = strip_new(row_dict.get("担当者", ""))
        instructors = (
            [x.strip() for x in re.split(r"[,、\n]", instr_raw) if x.strip()]
            if instr_raw
            else []
        )
        target_raw = strip_new(row_dict.get("受講対象", ""))
        targets = (
            [
                parse_target_str(x)
                for x in re.split(r"[,、/\n]", target_raw)
                if x.strip()
            ]
            if target_raw
            else []
        )

        if not name and not code:
            return None

        return ChangeEntry(
            change_type="create",
            course_code=code or None,
            course_name=name,
            term=term or None,
            day=day,
            period=period,
            schedules=scheds,
            instructors=instructors,
            room=room or None,
            targets=targets,
            changes=[],
        )

    elif has_arrow:
        # Updates
        field_changes: list[FieldChange] = []
        for col, cell_val in row_dict.items():
            if col in ("変更",):
                continue
            if cell_val and ("→" in cell_val or "->" in cell_val):
                parts = re.split(r"→|->", cell_val, maxsplit=1)
                old_v = clean_text(parts[0]) or None
                new_v = clean_text(parts[1]) if len(parts) > 1 else None
                new_v = new_v or None
                if old_v in ("-", ""):
                    old_v = None
                if new_v in ("-", ""):
                    new_v = None
                if old_v is None and new_v is None:
                    continue
                if old_v == new_v:
                    continue
                field_changes.append(
                    FieldChange(field=col, old_value=old_v, new_value=new_v)
                )

        if not field_changes:
            return None

        def get_unchanged_or_old(col: str) -> str:
            v = row_dict.get(col, "")
            if "→" in v or "->" in v:
                return clean_text(re.split(r"→|->", v, maxsplit=1)[0])
            return clean_text(v)

        code = get_unchanged_or_old("講義コード")
        name = get_unchanged_or_old("科目名")
        term = get_unchanged_or_old("学期")
        sched_raw = get_unchanged_or_old("曜日時限")
        day, period, scheds = parse_schedules(sched_raw)

        if not name and not code:
            return None

        return ChangeEntry(
            change_type="update",
            course_code=code or None,
            course_name=name,
            term=term or None,
            day=day,
            period=period,
            schedules=scheds,
            changes=field_changes,
        )

    return None


def _deduplicate_entries(entries: list[ChangeEntry]) -> list[ChangeEntry]:
    """Deduplicate identical change entries while preserving original order."""
    seen: set[tuple[Any, ...]] = set()
    deduped: list[ChangeEntry] = []
    for e in entries:
        key = (
            e.change_type,
            e.course_code,
            e.course_name,
            e.term,
            e.day,
            e.period,
            tuple(
                (fc.field, fc.old_value, fc.new_value) for fc in e.changes
            ),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    return deduped


def extract_changelog_from_pdf_tables(pdf_bytes: bytes) -> list[ChangeEntry]:
    """Extract changelog entries from vector PDF tables using pdfplumber."""
    all_entries: list[ChangeEntry] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        current_headers: list[str] | None = None
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                header_idx = -1
                for idx, row in enumerate(table[:5]):
                    detected = _detect_headers(row)
                    if detected:
                        current_headers = detected
                        header_idx = idx
                        break

                if header_idx >= 0:
                    data_rows = table[header_idx + 1 :]
                elif current_headers and len(table[0]) == len(current_headers):
                    data_rows = table
                else:
                    continue

                for row in data_rows:
                    entry = _parse_table_row(row, current_headers)
                    if entry:
                        all_entries.append(entry)

    return _deduplicate_entries(all_entries)


def _parse_gemini_json(raw_text: str) -> list[ChangeEntry]:
    parsed = ChangelogResponse.model_validate_json(raw_text.strip())
    return parsed.entries


def _generate_changes_with_model(model: str, pdf_bytes: bytes) -> list[ChangeEntry]:
    raw_text = generate_pdf_json(
        client=create_client(),
        model=model,
        pdf_bytes=pdf_bytes,
        prompt=GEMINI_CHANGELOG_PROMPT,
        response_schema=ChangelogResponse.model_json_schema(),
    )
    return _parse_gemini_json(raw_text)


def parse_changelog(pdf_bytes: bytes) -> list[ChangeEntry]:
    """Parse changelog PDF bytes into a list of ChangeEntry.

    Attempts table-based extraction via pdfplumber first.
    If no changelog table or entries are found, falls back to Gemini.
    """
    try:
        entries = extract_changelog_from_pdf_tables(pdf_bytes)
        if entries:
            logger.info(
                "Successfully extracted %d changelog entries from PDF tables",
                len(entries),
            )
            return entries
        logger.info(
            "No changelog table entries found via pdfplumber; falling back to Gemini model"
        )
    except Exception as e:
        logger.info(
            "Table-based extraction failed (%s); falling back to Gemini model",
            e,
        )

    return run_with_model_fallback(
        primary_model=Settings.GEMINI_MODEL,
        fallback_model=Settings.GEMINI_FALLBACK_MODEL,
        runner=lambda model: _generate_changes_with_model(model, pdf_bytes),
        logger=logger,
    )

