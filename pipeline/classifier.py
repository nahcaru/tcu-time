from __future__ import annotations

import json
import logging
from io import BytesIO

import pdfplumber
from google import genai

from pipeline.config import Config
from pipeline.models import PageClassification

logger = logging.getLogger(__name__)

def _build_prompt(page_summaries_json: str) -> str:
    return f"""以下は東京都市大学の授業時間表 PDF の各ページの概要です。
各ページの種類を分類してください。

分類カテゴリ:
- "course_table_spring": 前期の科目テーブル
- "course_table_fall": 後期の科目テーブル
- "cover": 表紙・日程
- "notes": 注意事項・学事暦
- "schedule": スケジュール表
- "map": キャンパスマップ
- "manual": マニュアル
- "other": その他

各ページの概要:
{page_summaries_json}

各 course_table のページについては、テーブルのヘッダー行
（列の並び順）も特定してください。

JSON 形式で出力:
[
  {{"page": 1, "type": "cover", "headers": null}},
  {{"page": 7, "type": "course_table_spring", "headers": ["曜", "限", "学期", ...]}}
]"""

def _request_classification(model: str, prompt: str) -> list[PageClassification]:
    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    if not response.text:
        raise ValueError("Gemini response did not include text")

    parsed = json.loads(response.text)
    if not isinstance(parsed, list):
        raise ValueError("Gemini JSON response must be a list")

    return [PageClassification.model_validate(item) for item in parsed]

def classify_pages(pdf_bytes: bytes) -> list[PageClassification]:
    page_summaries: list[dict[str, object]] = []

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []

            col_count = 0
            if tables:
                row_lengths = [
                    len(row)
                    for table in tables
                    for row in table
                    if row is not None
                ]
                if row_lengths:
                    col_count = max(row_lengths)

            page_summaries.append(
                {
                    "page": idx,
                    "has_table": bool(tables),
                    "col_count": col_count,
                    "text_preview": text[:300],
                }
            )

    page_summaries_json = json.dumps(page_summaries, ensure_ascii=False, indent=2)
    prompt = _build_prompt(page_summaries_json)

    try:
        return _request_classification(Config.GEMINI_MODEL, prompt)
    except (ValueError, json.JSONDecodeError, Exception) as primary_error:
        logger.warning(
            "Primary Gemini model failed (%s): %s",
            Config.GEMINI_MODEL,
            primary_error,
        )

    return _request_classification(Config.GEMINI_FALLBACK_MODEL, prompt)


def get_course_table_pages(
    classifications: list[PageClassification],
) -> list[PageClassification]:
    return [
        page
        for page in classifications
        if page.type in {"course_table_spring", "course_table_fall"}
    ]
