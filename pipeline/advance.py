from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import cast

import pdfplumber
from google import genai

from .config import Config
from . import db

logger = logging.getLogger(__name__)


def _request_course_names(model: str, all_text: str) -> list[str]:
    prompt = f"""以下は東京都市大学の先行履修に関する PDF から抽出したテキストです。
先行履修が可能な授業科目名をすべてリストアップしてください。
授業科目区分は不要です。科目名のみを JSON 配列で出力してください。

入力テキスト:
{all_text}
"""

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

    parsed_obj = json.loads(response.text)
    if not isinstance(parsed_obj, list):
        raise ValueError("Gemini JSON response must be a list")
    parsed = cast(list[object], parsed_obj)

    names: list[str] = []
    for item in parsed:
        if not isinstance(item, str):
            raise ValueError("Gemini JSON response must be a list of strings")
        names.append(item)

    return names


def extract_course_names(pdf_bytes: bytes) -> list[str]:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        texts = [(page.extract_text() or "") for page in pdf.pages]
    all_text = "\n".join(texts)

    try:
        return _request_course_names(Config.GEMINI_MODEL, all_text)
    except Exception as primary_error:
        logger.warning(
            "Primary Gemini model failed (%s): %s",
            Config.GEMINI_MODEL,
            primary_error,
        )

    return _request_course_names(Config.GEMINI_FALLBACK_MODEL, all_text)


def update_flags(course_names: list[str], academic_year: int) -> None:
    _ = db.reset_advance_enrollment(academic_year)

    updated_count = 0
    unmatched_count = 0

    for name in course_names:
        matched_courses = db.find_courses_by_name(name, academic_year)
        if not matched_courses:
            logger.warning("No matching course found for advance enrollment: %s", name)
            unmatched_count += 1
            continue

        for course in matched_courses:
            course_id = str(course["id"])
            _ = db.set_advance_enrollment(course_id)
            updated_count += 1

    logger.info(
        "Updated %d courses with advance_enrollment flag (%d names unmatched)",
        updated_count,
        unmatched_count,
    )
