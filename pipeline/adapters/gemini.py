from __future__ import annotations

import logging
from typing import Callable, TypeVar

from google import genai
from google.genai import types

from pipeline.core.settings import Settings

T = TypeVar("T")


def create_client() -> genai.Client:
    return genai.Client(api_key=Settings.GEMINI_API_KEY)


def build_pdf_part(pdf_bytes: bytes) -> types.Part:
    return types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")


def generate_pdf_json(
    *,
    client: genai.Client,
    model: str,
    pdf_bytes: bytes,
    prompt: str,
    response_schema: dict,
) -> str:
    response = client.models.generate_content(
        model=model,
        contents=[build_pdf_part(pdf_bytes), prompt],
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=response_schema,
        ),
    )

    if not response.text:
        raise ValueError("Gemini response did not include text")

    return response.text


def run_with_model_fallback(
    *,
    primary_model: str,
    fallback_model: str,
    runner: Callable[[str], T],
    logger: logging.Logger,
) -> T:
    try:
        return runner(primary_model)
    except Exception as primary_error:
        logger.warning(
            "Primary Gemini model failed (%s): %s. Falling back to %s",
            primary_model,
            primary_error,
            fallback_model,
        )
        return runner(fallback_model)
