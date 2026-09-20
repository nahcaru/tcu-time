from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_text(text: str | None) -> str:
    """Basic NFKC normalization and whitespace strip."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def fullwidth_to_half(text: str) -> str:
    """Convert fullwidth characters to halfwidth using NFKC."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def normalize_instructor_name(name: str | None) -> str:
    """Normalize instructor name.

    - Convert fullwidth spaces (\u3000) and consecutive whitespace to a single halfwidth space.
    - Strip leading and trailing whitespace.
    - Apply NFKC normalization.
    - Empty or whitespace-only strings become "".
    """
    if not name:
        return ""
    # Replace all whitespace characters (including \u3000, tabs, newlines) with single halfwidth space
    s = re.sub(r"[\s\u3000]+", " ", name)
    s = unicodedata.normalize("NFKC", s).strip()
    return s


def normalize_course_name(name: str | None) -> str:
    """Normalize course name.

    - Convert fullwidth alphabets and digits to halfwidth (NFKC).
    - Convert fullwidth parentheses （） to halfwidth ().
    - Convert fullwidth slash ／ to halfwidth /.
    - Fix missing space after comma in English titles (e.g. 'Intelligence,Adv.' -> 'Intelligence, Adv.').
    - Consolidate consecutive spaces to a single space.
    - Strip leading and trailing whitespace.
    """
    if not name:
        return ""
    # NFKC converts fullwidth A-Z, a-z, 0-9, and ／ to /
    s = unicodedata.normalize("NFKC", name)
    # Ensure parentheses are halfwidth
    s = s.replace("（", "(").replace("）", ")")
    # Fix missing space after comma in Latin/English titles (e.g., 'Word,Word' -> 'Word, Word')
    s = re.sub(r"([A-Za-z0-9]),([A-Za-z0-9])", r"\1, \2", s)
    # Consolidate multiple spaces
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def normalize_room(room: str | None) -> str:
    """Normalize classroom name.

    - Convert fullwidth parentheses （） to halfwidth ().
    - Apply NFKC normalization.
    - Consolidate spaces and strip.
    """
    if not room:
        return ""
    s = unicodedata.normalize("NFKC", room)
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def normalize_target_note(note: str | None) -> str:
    """Normalize target note.

    - Convert fullwidth tilde ～ (U+FF5E) and wave dash 〜 (U+301C) to halfwidth tilde ~ (U+007E).
    - Convert fullwidth parentheses （） to halfwidth ().
    - Apply NFKC normalization.
    - Consolidate spaces and strip.
    """
    if not note:
        return ""
    s = note.replace("～", "~").replace("〜", "~")
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def normalize_note(note: str | None) -> str:
    """Normalize general course notes (e.g. 対開講)."""
    if not note:
        return ""
    s = unicodedata.normalize("NFKC", note)
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def normalize_course_dict(course: dict[str, Any]) -> dict[str, Any]:
    """Normalize all string fields in a course dictionary."""
    normalized = dict(course)
    if "name" in normalized and normalized["name"]:
        normalized["name"] = normalize_course_name(str(normalized["name"]))

    if "instructors" in normalized and isinstance(normalized["instructors"], list):
        cleaned_instructors: list[str] = []
        for inst in normalized["instructors"]:
            n_inst = normalize_instructor_name(str(inst))
            if n_inst and n_inst not in cleaned_instructors:
                cleaned_instructors.append(n_inst)
        normalized["instructors"] = cleaned_instructors or ["未定"]

    if "room" in normalized and normalized["room"]:
        normalized["room"] = normalize_room(str(normalized["room"]))

    if "notes" in normalized and normalized["notes"]:
        normalized["notes"] = normalize_note(str(normalized["notes"]))

    if "targets" in normalized and isinstance(normalized["targets"], list):
        new_targets: list[dict[str, Any]] = []
        for t in normalized["targets"]:
            if isinstance(t, dict):
                t_dict = dict(t)
                if "target_name" in t_dict and t_dict["target_name"]:
                    t_dict["target_name"] = normalize_text(str(t_dict["target_name"]))
                if "note" in t_dict and t_dict["note"]:
                    t_dict["note"] = normalize_target_note(str(t_dict["note"]))
                new_targets.append(t_dict)
        normalized["targets"] = new_targets

    return normalized
