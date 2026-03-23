"""Advance enrollment parser — extracts course names from advance enrollment PDFs.

Changed from previous design: update_flags() no longer writes to the DB.
Extracted names are returned for the caller to save as raw_json in the
extractions table. DB reflection happens only after admin approval via
db.approve_extraction().
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import cast

import pdfplumber
from google import genai

from .config import Config

logger = logging.getLogger(__name__)


from pydantic import BaseModel, Field
from google.genai import types


class AdvanceEnrollmentResponse(BaseModel):
    course_names: list[str] = Field(description="List of advance enrollment course names")


def _request_course_names(model: str, pdf_bytes: bytes) -> list[str]:
    prompt = """以下は東京都市大学の先行履修に関する PDF です。
先行履修が可能な授業科目名をすべてリストアップしてください。
授業科目区分は不要です。
"""

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf"
            ),
            prompt
        ],
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=AdvanceEnrollmentResponse.model_json_schema(),
        ),
    )

    if not response.text:
        raise ValueError("Gemini response did not include text")

    parsed = AdvanceEnrollmentResponse.model_validate_json(response.text)
    return parsed.course_names


def extract_course_names(pdf_bytes: bytes) -> list[str]:
    """Extract advance-enrollment course names from a PDF.

    Does NOT update flags in the DB. Returns a list of course name strings
    to be saved as raw_json in the extractions table.
    Admin approval (via db.approve_extraction) triggers DB flag updates.
    """
    try:
        return _request_course_names(Config.GEMINI_MODEL, pdf_bytes)
    except Exception as primary_error:
        logger.warning(
            "Primary Gemini model failed (%s): %s",
            Config.GEMINI_MODEL,
            primary_error,
        )

    return _request_course_names(Config.GEMINI_FALLBACK_MODEL, pdf_bytes)

