"""Validation rules for extracted courses to catch OCR/LLM misclassifications early."""

from __future__ import annotations

from typing import Any, Literal

from pipeline.models import VALID_DAYS, ExtractedCourse

Severity = Literal["error", "warning", "info"]

SPRING_TERMS = {"前期前", "前期後", "前期", "前集中"}
FALL_TERMS = {"後期前", "後期後", "後期", "後集中"}


class ValidationWarning:
    __slots__ = ("code", "name", "field", "message", "severity")

    def __init__(
        self,
        code: str,
        name: str,
        field: str,
        message: str,
        severity: Severity,
    ) -> None:
        self.code = code
        self.name = name
        self.field = field
        self.message = message
        self.severity = severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
        }


def validate_extracted_courses(
    courses: list[ExtractedCourse] | list[dict[str, Any]],
    semester: str | None = None,
) -> list[dict[str, Any]]:
    """Inspect extracted courses for logical contradictions, missing fields, or OCR corruption.

    Returns a list of warning dicts for admin UI display and logging.
    """
    warnings: list[ValidationWarning] = []

    for item in courses:
        if hasattr(item, "model_dump") and callable(item.model_dump):
            c_dict = item.model_dump()
        elif isinstance(item, dict):
            c_dict = item
        else:
            c_dict = {}

        if not isinstance(c_dict, dict):
            c_dict = {}

        code = str(c_dict.get("code", "") or "").strip()
        name = str(c_dict.get("name", "") or "").strip()
        term = str(c_dict.get("term", "") or "").strip()
        room = str(c_dict.get("room", "") or "").strip()
        class_sec = str(c_dict.get("class_section", "") or "").strip()

        instructors_raw = c_dict.get("instructors")
        instructors = (
            instructors_raw if isinstance(instructors_raw, (list, tuple)) else []
        )

        schedules_raw = c_dict.get("schedules")
        schedules = schedules_raw if isinstance(schedules_raw, (list, tuple)) else []

        has_regular_slots = any(
            isinstance(s, dict)
            and s.get("day") in VALID_DAYS
            and s.get("period") is not None
            and 1 <= s.get("period") <= 5
            for s in schedules
        )

        # 1. Digits in class_section (period misclassification)
        if class_sec.isdigit():
            warnings.append(
                ValidationWarning(
                    code=code,
                    name=name,
                    field="class_section",
                    message=f"クラス区分に時限数字 '{class_sec}' が混入しています。",
                    severity="warning",
                )
            )

        # 2. Weekly schedule vs Intensive Term contradiction
        if has_regular_slots and term in ("前集中", "後集中"):
            warnings.append(
                ValidationWarning(
                    code=code,
                    name=name,
                    field="term",
                    message=f"通常スケジュールが存在しますが、学期が '{term}' に設定されています。",
                    severity="warning",
                )
            )

        # 3. Course code prefix vs Term / Semester contradiction
        if len(code) >= 3:
            code_sem_char = code[2].lower()
            if code_sem_char == "b" and term in SPRING_TERMS:
                warnings.append(
                    ValidationWarning(
                        code=code,
                        name=name,
                        field="term",
                        message=f"講義コード {code} は後期科目ですが、学期が '{term}' になっています。",
                        severity="error",
                    )
                )
            elif code_sem_char == "a" and term in FALL_TERMS:
                warnings.append(
                    ValidationWarning(
                        code=code,
                        name=name,
                        field="term",
                        message=f"講義コード {code} は前期科目ですが、学期が '{term}' になっています。",
                        severity="error",
                    )
                )

        # 4. Missing classroom for regular courses
        if has_regular_slots and not room:
            warnings.append(
                ValidationWarning(
                    code=code,
                    name=name,
                    field="room",
                    message="通常開講科目ですが、教室名が設定されていません。",
                    severity="info",
                )
            )

        # 5. Undetermined instructor
        cleaned_instructors = [str(i).strip() for i in instructors if str(i).strip()]
        if not cleaned_instructors or cleaned_instructors == ["未定"]:
            warnings.append(
                ValidationWarning(
                    code=code,
                    name=name,
                    field="instructors",
                    message="担当教員が未設定または '未定' です。",
                    severity="info",
                )
            )

    return [w.to_dict() for w in warnings]
