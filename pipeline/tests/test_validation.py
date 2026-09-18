"""Tests for pipeline/core/validator.py and timetable extractor sanitizations."""

from __future__ import annotations

from pipeline.core.validator import validate_extracted_courses
from pipeline.extractors.timetable import _raw_to_extracted_course
from pipeline.models import ExtractedCourse, Schedule, Semester


def test_sanitize_class_section_digits():
    raw = {
        "code": "smba030031",
        "name": "先端デバイス特論",
        "instructors": ["野平 博司"],
        "class_section": "3",  # Period mistakenly placed in class_section
        "term": "後期前",
        "room": "1BK",
        "day": "金",
        "period": 3,
    }
    course = _raw_to_extracted_course(raw, semester=Semester.FALL)
    assert course is not None
    assert course.class_section == ""  # Sanitized to empty string


def test_preserve_notes_paired_slots():
    raw = {
        "code": "smba030031",
        "name": "先端デバイス特論",
        "instructors": ["野平 博司"],
        "notes": "対開講(金3,金4)",
        "term": "後期前",
        "room": "1BK",
        "day": "金",
        "period": 3,
    }
    course = _raw_to_extracted_course(raw, semester=Semester.FALL)
    assert course is not None
    assert course.notes == "対開講(金3,金4)"  # Preserved as in original PDF table


def test_fix_smbz_term_leakage():
    # smbz (Fall course) with regular schedule should not stay '後期前' if mistakenly propagated
    raw = {
        "code": "smbz000191",
        "name": "英語プレゼンテーション技法",
        "instructors": ["ボルジロフスカヤ アンナ"],
        "term": "後期前",
        "room": "13A",
        "day": "木",
        "period": 4,
    }
    course = _raw_to_extracted_course(raw, semester=Semester.FALL)
    assert course is not None
    assert course.term == "後期"  # Corrected from 後期前 to 後期


def test_validate_clean_courses():
    courses = [
        ExtractedCourse(
            code="smba010011",
            name="先進材料工学特論",
            instructors=["佐藤 一郎"],
            term="後期前",
            room="13C",
            semester=Semester.FALL,
            schedules=[Schedule(day="火", period=1)],
        )
    ]
    warnings = validate_extracted_courses(courses)
    assert len(warnings) == 0


def test_validate_schedule_vs_intensive_contradiction():
    courses = [
        ExtractedCourse(
            code="smbz010041",
            name="流体力学特論",
            instructors=["佐藤"],
            term="後集中",
            room="12A",
            semester=Semester.FALL,
            schedules=[Schedule(day="火", period=1)],
        )
    ]
    warnings = validate_extracted_courses(courses)
    assert len(warnings) == 1
    assert warnings[0]["field"] == "term"
    assert warnings[0]["severity"] == "warning"
    assert "通常スケジュールが存在します" in warnings[0]["message"]


def test_validate_code_vs_term_contradiction():
    courses = [
        ExtractedCourse(
            code="smba010011",
            name="テスト科目",
            instructors=["田中"],
            term="前期前",
            room="11B",
            semester=Semester.FALL,
            schedules=[Schedule(day="水", period=2)],
        )
    ]
    warnings = validate_extracted_courses(courses)
    term_errors = [
        w for w in warnings if w["field"] == "term" and w["severity"] == "error"
    ]
    assert len(term_errors) == 1
    assert "後期科目ですが" in term_errors[0]["message"]


def test_validate_missing_classroom():
    courses = [
        ExtractedCourse(
            code="smaa010021",
            name="情報科学特論",
            instructors=["鈴木"],
            term="前期前",
            room="",
            semester=Semester.SPRING,
            schedules=[Schedule(day="木", period=3)],
        )
    ]
    warnings = validate_extracted_courses(courses)
    room_warnings = [w for w in warnings if w["field"] == "room"]
    assert len(room_warnings) == 1
    assert room_warnings[0]["severity"] == "info"
