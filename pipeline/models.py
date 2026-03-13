import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, field_validator


VALID_DAYS = {"月", "火", "水", "木", "金", "土"}
VALID_TERMS = {
    "前期前",
    "前期後",
    "前期",
    "前集中",
    "後期前",
    "後期後",
    "後期",
    "後集中",
    "通年",
}
# Course code format: sm + 2 lowercase letters + 6 digits (e.g. smab020161)
COURSE_CODE_PATTERN = re.compile(r"^sm[a-z]{2}\d{6}$")


# ---------------------------------------------------------------------------
# Enums for pipeline metadata
# ---------------------------------------------------------------------------


class PDFType(str, Enum):
    TIMETABLE = "timetable"
    CHANGELOG = "changelog"
    ADVANCE_ENROLLMENT = "advance_enrollment"


class Semester(str, Enum):
    SPRING = "spring"
    FALL = "fall"


# ---------------------------------------------------------------------------
# Page classification (from Gemini classifier)
# ---------------------------------------------------------------------------

PageType = Literal[
    "course_table_spring",
    "course_table_fall",
    "cover",
    "notes",
    "schedule",
    "map",
    "manual",
    "other",
]


class PageClassification(BaseModel):
    """Classification of a single PDF page by the Gemini classifier."""

    page: int  # 1-indexed page number
    type: PageType
    headers: list[str] | None = None  # Column headers if course_table


# ---------------------------------------------------------------------------
# PDF metadata (from monitor link classification)
# ---------------------------------------------------------------------------


class PDFMetadata(BaseModel):
    """Metadata about a PDF link derived from link text / context."""

    pdf_type: PDFType
    semester: Semester | None = None  # None when both semesters in one PDF
    is_tentative: bool = False


# ---------------------------------------------------------------------------
# Changelog models
# ---------------------------------------------------------------------------

ChangeType = Literal["add", "modify", "cancel"]


class FieldChange(BaseModel):
    """A single field-level change within a changelog entry."""

    field: str
    old_value: str | None = None
    new_value: str | None = None

    @field_validator("old_value", "new_value", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str | None:
        """Gemini sometimes returns numeric values for fields like period."""
        if v is None:
            return None
        return str(v)


class ChangeEntry(BaseModel):
    """A single entry from a changelog PDF."""

    change_type: ChangeType
    course_code: str | None = None
    course_name: str
    term: str | None = None
    day: str | None = None
    period: int | str | None = None
    changes: list[FieldChange] = []
    reason: str | None = None

    @field_validator("period", mode="before")
    @classmethod
    def coerce_period(cls, v: object) -> int | str | None:
        """Gemini may return period as int, numeric string, or text like '集中'."""
        if v is None:
            return None
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return s


class Schedule(BaseModel):
    term: str
    day: str
    period: int
    room: str = ""

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        if v not in VALID_DAYS:
            raise ValueError(f"Invalid day: {v}. Must be one of {VALID_DAYS}")
        return v

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError(f"Invalid period: {v}. Must be 1-5")
        return v

    @field_validator("term")
    @classmethod
    def validate_term(cls, v: str) -> str:
        if v not in VALID_TERMS:
            raise ValueError(f"Invalid term: {v}. Must be one of {VALID_TERMS}")
        return v


class CourseTarget(BaseModel):
    target_code: str
    target_name: str
    note: str = ""


class ExtractedCourse(BaseModel):
    code: str
    name: str
    instructors: list[str]
    year_level: int = 1
    class_section: str = ""
    semester: Semester | None = None
    schedules: list[Schedule]
    target_raw: str = ""
    targets: list[CourseTarget] = []
    notes: str = ""

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not COURSE_CODE_PATTERN.match(v):
            raise ValueError(
                f"Invalid course code: {v}. Must match pattern sm[a-z]{{2}}[0-9]{{6}}"
            )
        return v

    @field_validator("instructors")
    @classmethod
    def validate_instructors(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Instructors list must not be empty")
        return v


class CourseMetadata(BaseModel):
    curriculum_code: str
    category: str | None = None
    credits: float | None = None


class ExtractionResult(BaseModel):
    pdf_url: str
    pdf_hash: str
    pdf_type: PDFType = PDFType.TIMETABLE
    semester: Semester | None = None
    is_tentative: bool = False
    academic_year: int | None = None
    courses: list[ExtractedCourse]
    errors: list[str] = []
