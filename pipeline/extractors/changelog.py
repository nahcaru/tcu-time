from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from pipeline.adapters.gemini import (
    create_client,
    generate_pdf_json,
    run_with_model_fallback,
)
from pipeline.core.settings import Settings
from pipeline.models import ChangeEntry

logger = logging.getLogger(__name__)


class ChangelogResponse(BaseModel):
    entries: list[ChangeEntry] = Field(
        description="List of changelog items extracted from text"
    )


def _parse_gemini_json(raw_text: str) -> list[ChangeEntry]:
    parsed = ChangelogResponse.model_validate_json(raw_text.strip())
    return parsed.entries


def _generate_changes_with_model(model: str, pdf_bytes: bytes) -> list[ChangeEntry]:
    prompt = """
以下は東京都市大学の授業時間表の変更一覧です。
各変更エントリを JSON として出力してください。
"""
    raw_text = generate_pdf_json(
        client=create_client(),
        model=model,
        pdf_bytes=pdf_bytes,
        prompt=prompt,
        response_schema=ChangelogResponse.model_json_schema(),
    )
    return _parse_gemini_json(raw_text)


def parse_changelog(pdf_bytes: bytes) -> list[ChangeEntry]:
    return run_with_model_fallback(
        primary_model=Settings.GEMINI_MODEL,
        fallback_model=Settings.GEMINI_FALLBACK_MODEL,
        runner=lambda model: _generate_changes_with_model(model, pdf_bytes),
        logger=logger,
    )
