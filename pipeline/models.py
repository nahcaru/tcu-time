import re
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
    courses: list[ExtractedCourse]
    errors: list[str] = []
