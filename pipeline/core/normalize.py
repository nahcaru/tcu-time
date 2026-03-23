from __future__ import annotations

import unicodedata


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def fullwidth_to_half(text: str) -> str:
    return unicodedata.normalize("NFKC", text)
