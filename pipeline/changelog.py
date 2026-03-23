"""Changelog parser — parses change-list PDFs via Gemini API.

Changed from previous design: apply_changelog() no longer writes to the DB.
Parsed changes are returned as a list of ChangeEntry for the caller to save
as raw_json in the extractions table. DB reflection happens only after
admin approval via db.approve_extraction().
"""

from __future__ import annotations

import json
import logging
from io import BytesIO

import pdfplumber
from google import genai

from pipeline.config import Config
from pipeline.models import ChangeEntry, FieldChange

logger = logging.getLogger(__name__)


from pydantic import BaseModel, Field

from google.genai import types

class ChangelogResponse(BaseModel):
    entries: list[ChangeEntry] = Field(description="List of changelog items extracted from text")



def _parse_gemini_json(raw_text: str) -> list[ChangeEntry]:
    parsed = ChangelogResponse.model_validate_json(raw_text.strip())
    return parsed.entries


def _generate_changes_with_model(client: genai.Client, model: str, pdf_bytes: bytes) -> list[ChangeEntry]:
    prompt = """
以下は東京都市大学の授業時間表の変更一覧です。
各変更エントリを JSON として出力してください。
"""

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
            response_json_schema=ChangelogResponse.model_json_schema(),
        ),
    )
    return _parse_gemini_json(response.text or "")


def parse_changelog(pdf_bytes: bytes) -> list[ChangeEntry]:
    """Parse a changelog PDF and return structured change entries.

    Does NOT apply changes to the DB. Returns a list of ChangeEntry
    objects to be saved as raw_json in the extractions table.
    Admin approval (via db.approve_extraction) triggers DB reflection.
    """
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

    try:
        return _generate_changes_with_model(client, Config.GEMINI_MODEL, pdf_bytes)
    except Exception as primary_error:
        logger.warning(
            "Primary Gemini model failed for changelog parsing: %s. Falling back to %s",
            primary_error,
            Config.GEMINI_FALLBACK_MODEL,
        )
        return _generate_changes_with_model(client, Config.GEMINI_FALLBACK_MODEL, pdf_bytes)

