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


def discover_available_flash_model(client: genai.Client | None = None) -> str:
    """Find the latest available Gemini Flash model supported by the API key."""
    if client is None:
        client = create_client()
    try:
        candidates: list[str] = []
        for model in client.models.list():
            name = model.name.replace("models/", "")
            if (
                "flash" in name.lower()
                and "tts" not in name
                and "image" not in name
                and "audio" not in name
            ):
                candidates.append(name)
        if "gemini-flash-latest" in candidates:
            return "gemini-flash-latest"
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0]
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Failed to query models list from Gemini API: %s", exc
        )

    return "gemini-2.5-flash"


def run_with_model_fallback(
    *,
    primary_model: str,
    fallback_model: str,
    runner: Callable[[str], T],
    logger: logging.Logger,
    client: genai.Client | None = None,
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
        try:
            return runner(fallback_model)
        except Exception as fallback_error:
            logger.warning(
                "Fallback Gemini model failed (%s): %s. Attempting dynamic model discovery...",
                fallback_model,
                fallback_error,
            )
            try:
                discovered = discover_available_flash_model(client)
                if discovered not in (primary_model, fallback_model):
                    logger.info(
                        "Retrying with dynamically discovered model: %s", discovered
                    )
                    return runner(discovered)
            except Exception as disc_exc:
                logger.error("Dynamic discovery failed: %s", disc_exc)
            raise fallback_error from primary_error
