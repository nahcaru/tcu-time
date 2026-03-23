"""Tests for pipeline/extractor.py (Gemini-based extraction)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ..extractor import (
    _raw_to_extracted_course,
    deduplicate_courses,
)
from ..models import CourseTarget, ExtractedCourse, Schedule, Semester


# ---------------------------------------------------------------------------
# Model validation (unchanged rules)
# ---------------------------------------------------------------------------


class TestExtractedCourse:
    def test_valid_course(self) -> None:
        course = ExtractedCourse(
            code="smab020161",
            name="ロボティクス特論",
            instructors=["佐藤 大祐"],
            schedules=[
                Schedule(term="前期後", day="月", period=1, room="22A"),
                Schedule(term="前期後", day="木", period=1, room="22A"),
            ],
            targets=[CourseTarget(target_code="02", target_name="機械")],
            target_raw="対象[02機械]",
        )
        assert course.code == "smab020161"
        assert len(course.schedules) == 2

    def test_invalid_course_code(self) -> None:
        with pytest.raises(ValueError, match="Invalid course code"):
            ExtractedCourse(
                code="invalid",
                name="Test",
                instructors=["Teacher"],
                schedules=[Schedule(term="前期", day="月", period=1)],
            )

    def test_invalid_day(self) -> None:
        with pytest.raises(ValueError, match="Invalid day"):
            Schedule(term="前期", day="日", period=1)

    def test_invalid_period(self) -> None:
        with pytest.raises(ValueError, match="Invalid period"):
            Schedule(term="前期", day="月", period=6)

    def test_empty_instructors(self) -> None:
        with pytest.raises(ValueError, match="Instructors list must not be empty"):
            ExtractedCourse(
                code="smab020161",
                name="Test",
                instructors=[],
                schedules=[Schedule(term="前期", day="月", period=1)],
            )


# ---------------------------------------------------------------------------
# _raw_to_extracted_course (Gemini JSON → ExtractedCourse)
# ---------------------------------------------------------------------------


class TestRawToExtractedCourse:
    def test_valid_simple(self) -> None:
        raw = {
            "code": "smab020161",
            "name": "ロボティクス特論",
            "instructors": ["佐藤 大祐"],
            "year_level": 1,
            "class_section": "",
            "term": "前期後",
            "day": "月",
            "period": 1,
            "room": "22A",
            "targets": [{"target_code": "02", "target_name": "機械", "note": ""}],
            "target_raw": "対象[02機械]",
            "notes": "",
        }
        course = _raw_to_extracted_course(raw, Semester.SPRING)
        assert course is not None
        assert course.code == "smab020161"
        assert len(course.schedules) == 1
        assert course.schedules[0].day == "月"
        assert len(course.targets) == 1

    def test_invalid_code_returns_none(self) -> None:
        raw = {
            "code": "INVALID",
            "name": "Test",
            "instructors": ["Teacher"],
            "term": "前期",
            "day": "月",
            "period": 1,
        }
        assert _raw_to_extracted_course(raw, None) is None

    def test_missing_code_returns_none(self) -> None:
        raw = {"name": "Test", "instructors": ["Teacher"]}
        assert _raw_to_extracted_course(raw, None) is None

    def test_empty_instructors_defaults_to_mitei(self) -> None:
        raw = {
            "code": "smab020161",
            "name": "Test",
            "instructors": [],
            "term": "前期",
            "day": "月",
            "period": 1,
        }
        course = _raw_to_extracted_course(raw, None)
        assert course is not None
        assert course.instructors == ["未定"]

    def test_paired_slots(self) -> None:
        raw = {
            "code": "smab020161",
            "name": "ロボティクス特論",
            "instructors": ["佐藤 大祐"],
            "term": "前期後",
            "day": "月",
            "period": 1,
            "room": "22A",
            "paired_slots": [
                {"day": "月", "period": 1},
                {"day": "木", "period": 1},
            ],
        }
        course = _raw_to_extracted_course(raw, Semester.SPRING)
        assert course is not None
        assert len(course.schedules) == 2
        days = {s.day for s in course.schedules}
        assert days == {"月", "木"}

    def test_invalid_day_in_schedule_skipped(self) -> None:
        """Courses with invalid day in schedule should be skipped gracefully."""
        raw = {
            "code": "smab020161",
            "name": "Test",
            "instructors": ["Teacher"],
            "term": "前期",
            "day": "日",  # invalid
            "period": 1,
        }
        course = _raw_to_extracted_course(raw, None)
        # Course still created but with no valid schedules
        assert course is not None
        assert course.schedules == []

    def test_intensive_no_schedule(self) -> None:
        raw = {
            "code": "smab020161",
            "name": "集中講義",
            "instructors": ["佐藤"],
            "term": "前集中",
            "day": "",
            "period": None,
        }
        course = _raw_to_extracted_course(raw, None)
        assert course is not None
        assert course.schedules == []


# ---------------------------------------------------------------------------
# deduplicate_courses
# ---------------------------------------------------------------------------


class TestDeduplicateCourses:
    def test_same_code_merges_schedules(self) -> None:
        c1 = ExtractedCourse(
            code="smab020167",
            name="重複講義",
            instructors=["佐藤 太郎"],
            schedules=[Schedule(term="前期", day="月", period=1, room="22A")],
        )
        c2 = ExtractedCourse(
            code="smab020167",
            name="重複講義",
            instructors=["佐藤 太郎"],
            schedules=[Schedule(term="前期", day="木", period=1, room="22B")],
        )
        merged = deduplicate_courses([c1, c2])
        assert len(merged) == 1
        assert len(merged[0].schedules) == 2
        assert {(s.day, s.period) for s in merged[0].schedules} == {("月", 1), ("木", 1)}

    def test_different_codes_kept_separate(self) -> None:
        c1 = ExtractedCourse(
            code="smab020161",
            name="科目A",
            instructors=["佐藤"],
            schedules=[Schedule(term="前期", day="月", period=1)],
        )
        c2 = ExtractedCourse(
            code="smab020162",
            name="科目B",
            instructors=["鈴木"],
            schedules=[Schedule(term="前期", day="火", period=1)],
        )
        result = deduplicate_courses([c1, c2])
        assert len(result) == 2

    def test_duplicate_schedule_not_added_twice(self) -> None:
        c1 = ExtractedCourse(
            code="smab020167",
            name="重複講義",
            instructors=["佐藤"],
            schedules=[Schedule(term="前期", day="月", period=1, room="22A")],
        )
        c2 = ExtractedCourse(
            code="smab020167",
            name="重複講義",
            instructors=["佐藤"],
            schedules=[Schedule(term="前期", day="月", period=1, room="22A")],
        )
        merged = deduplicate_courses([c1, c2])
        assert len(merged[0].schedules) == 1


# ---------------------------------------------------------------------------
# extract_courses_from_pdf — integration (skipped without reference PDF)
# ---------------------------------------------------------------------------


class TestExtractCoursesFromPdfIntegration:
    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / "References" / "grad_timetable_front.pdf").exists(),
        reason="Reference PDF not found",
    )
    def test_extract_courses_from_reference_pdf(self, reference_pdf_path: Path) -> None:
        """Integration test using real Gemini API. Requires GEMINI_API_KEY env var."""
        from ..extractor import extract_courses_from_pdf

        pdf_bytes = reference_pdf_path.read_bytes()

        with patch("pipeline.extractor.Config") as mock_config:
            mock_config.GEMINI_API_KEY = "test"
            mock_config.GEMINI_MODEL = "gemini-1.5-flash"
            mock_config.GEMINI_FALLBACK_MODEL = "gemini-1.5-pro"

            courses = extract_courses_from_pdf(pdf_bytes)

        assert isinstance(courses, list)
