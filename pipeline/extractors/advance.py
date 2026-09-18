from __future__ import annotations

import io
import logging
import re
import unicodedata

import pdfplumber
from pydantic import BaseModel, Field

from pipeline.adapters.gemini import (
    create_client,
    generate_pdf_json,
    run_with_model_fallback,
)
from pipeline.core.settings import Settings

logger = logging.getLogger(__name__)


class AdvanceEnrollmentResponse(BaseModel):
    course_names: list[str] = Field(
        description="List of advance enrollment course names"
    )


def clean_text(s: str | None) -> str:
    """Normalize text and trim whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).strip()
    s = re.sub(r"-\s*\n\s*", "-", s)
    s = re.sub(r"([a-zA-Z0-9])\s*\n\s*([a-zA-Z0-9])", r"\1 \2", s)
    s = re.sub(r"\s*\n\s*", " ", s)
    return s.strip()


def extract_course_names_from_pdf_tables(pdf_bytes: bytes) -> list[str]:
    """Extract advance enrollment course names from vector PDF tables using pdfplumber."""
    names: list[str] = []
    seen: set[str] = set()

    ignored_keywords = {
        "科目名",
        "授業科目名",
        "科目",
        "授業科目",
        "授業科目区分",
        "科目区分",
        "専攻",
        "開講期",
        "学期",
        "単位",
        "単位数",
        "担当教員",
        "担当者",
        "備考",
        "-",
        "－",
        "なし",
    }

    last_col_idx: int | None = None
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                name_col_idx: int | None = None
                data_start_row = 0
                for row_idx, row in enumerate(table[:5]):
                    for col_idx, cell in enumerate(row):
                        if cell:
                            cell_text = clean_text(cell)
                            if cell_text in ("科目名", "授業科目名", "科目", "授業科目"):
                                name_col_idx = col_idx
                                break
                            elif "科目名" in cell_text or "授業科目" in cell_text:
                                name_col_idx = col_idx
                                break
                    if name_col_idx is not None:
                        data_start_row = row_idx + 1
                        last_col_idx = name_col_idx
                        break

                target_col = name_col_idx if name_col_idx is not None else last_col_idx
                if target_col is None:
                    continue

                for row in table[data_start_row:]:
                    if len(row) > target_col:
                        cell_val = row[target_col]
                        if not cell_val:
                            continue
                        for line in cell_val.splitlines():
                            cleaned = clean_text(line)
                            if (
                                cleaned
                                and cleaned not in ignored_keywords
                                and not cleaned.startswith("※")
                                and cleaned not in seen
                            ):
                                seen.add(cleaned)
                                names.append(cleaned)

    return names


def _request_course_names(model: str, pdf_bytes: bytes) -> list[str]:
    prompt = """以下は東京都市大学の先行履修に関する PDF です。
先行履修が可能な授業科目名をすべてリストアップしてください。
授業科目区分は不要です。
"""
    raw_text = generate_pdf_json(
        client=create_client(),
        model=model,
        pdf_bytes=pdf_bytes,
        prompt=prompt,
        response_schema=AdvanceEnrollmentResponse.model_json_schema(),
    )
    parsed = AdvanceEnrollmentResponse.model_validate_json(raw_text)
    return parsed.course_names


def extract_course_names(pdf_bytes: bytes) -> list[str]:
    """Extract course names from advance enrollment PDF.

    Attempts table-based extraction via pdfplumber first.
    If no table entries are found, falls back to Gemini.
    """
    try:
        names = extract_course_names_from_pdf_tables(pdf_bytes)
        if names:
            logger.info(
                "Successfully extracted %d advance enrollment courses via pdfplumber",
                len(names),
            )
            return names
        logger.info(
            "No course names found via pdfplumber tables; falling back to Gemini model"
        )
    except Exception as exc:
        logger.info(
            "pdfplumber extraction failed (%s); falling back to Gemini model", exc
        )

    return run_with_model_fallback(
        primary_model=Settings.GEMINI_MODEL,
        fallback_model=Settings.GEMINI_FALLBACK_MODEL,
        runner=lambda model: _request_course_names(model, pdf_bytes),
        logger=logger,
    )
