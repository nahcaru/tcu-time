from __future__ import annotations

import logging

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
    return run_with_model_fallback(
        primary_model=Settings.GEMINI_MODEL,
        fallback_model=Settings.GEMINI_FALLBACK_MODEL,
        runner=lambda model: _request_course_names(model, pdf_bytes),
        logger=logger,
    )
