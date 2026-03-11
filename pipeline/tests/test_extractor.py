from pathlib import Path

import pytest

from ..extractor import (
    _parse_instructors,
    carry_forward,
    deduplicate_courses,
    extract_courses_from_pdf,
    merge_multiline_rows,
    parse_intensive_row,
    parse_paired_slots,
    parse_regular_row,
    parse_targets,
)
from ..models import CourseTarget, ExtractedCourse, Schedule


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
        import pytest

        with pytest.raises(ValueError, match="Invalid course code"):
            ExtractedCourse(
                code="invalid",
                name="Test",
                instructors=["Teacher"],
                schedules=[Schedule(term="前期", day="月", period=1)],
            )

    def test_invalid_day(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Invalid day"):
            Schedule(term="前期", day="日", period=1)

    def test_invalid_period(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Invalid period"):
            Schedule(term="前期", day="月", period=6)

    def test_empty_instructors(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Instructors list must not be empty"):
            ExtractedCourse(
                code="smab020161",
                name="Test",
                instructors=[],
                schedules=[Schedule(term="前期", day="月", period=1)],
            )


class TestParseInstructors:
    def test_single_instructor(self) -> None:
        assert _parse_instructors("佐藤 大祐") == ["佐藤 大祐"]

    def test_empty_string_returns_default(self) -> None:
        assert _parse_instructors("") == ["未定"]

    def test_multiline_fragment_merge(self) -> None:
        raw = "神野 健哉\nニーナ スヴィリ\nドヴァ"
        assert _parse_instructors(raw) == ["神野 健哉", "ニーナ スヴィリドヴァ"]

    def test_special_standalone_kept(self) -> None:
        assert _parse_instructors("各教員") == ["各教員"]

    def test_foreign_name_with_middle_dot(self) -> None:
        assert _parse_instructors("M・テイボン") == ["M・テイボン"]

    def test_multiple_instructors_newlines(self) -> None:
        raw = "佐藤 太郎\n鈴木 花子"
        assert _parse_instructors(raw) == ["佐藤 太郎", "鈴木 花子"]


class TestParseTargets:
    def test_simple_target(self) -> None:
        targets = parse_targets("対象[09情報]")
        assert targets == [CourseTarget(target_code="09", target_name="情報")]

    def test_target_with_note(self) -> None:
        targets = parse_targets("対象[02機械/23以降入学生対象]")
        assert targets == [
            CourseTarget(target_code="02", target_name="機械", note="23以降入学生対象")
        ]

    def test_multi_target(self) -> None:
        targets = parse_targets("対象[10情報/0共通]")
        assert len(targets) == 2
        assert targets[0] == CourseTarget(target_code="10", target_name="情報")
        assert targets[1] == CourseTarget(target_code="0", target_name="共通")

    def test_wrapped_name(self) -> None:
        targets = parse_targets("対象[7建築都市デザイン]")
        assert targets == [CourseTarget(target_code="7", target_name="建築都市デザイン")]

    def test_no_match_returns_empty(self) -> None:
        assert parse_targets("なし") == []

    def test_empty_returns_empty(self) -> None:
        assert parse_targets("") == []


class TestParsePairedSlots:
    def test_standard_two_slots(self) -> None:
        schedules = parse_paired_slots("対開講(月1,木1)", "前期後")
        assert schedules == [
            Schedule(term="前期後", day="月", period=1),
            Schedule(term="前期後", day="木", period=1),
        ]

    def test_three_slots(self) -> None:
        schedules = parse_paired_slots("対開講(火2,火3,火4)", "前期")
        assert schedules == [
            Schedule(term="前期", day="火", period=2),
            Schedule(term="前期", day="火", period=3),
            Schedule(term="前期", day="火", period=4),
        ]

    def test_full_width_numbers(self) -> None:
        schedules = parse_paired_slots("対開講(月１,木１)", "前期後")
        assert schedules == [
            Schedule(term="前期後", day="月", period=1),
            Schedule(term="前期後", day="木", period=1),
        ]

    def test_no_match(self) -> None:
        assert parse_paired_slots("通常", "前期") == []


class TestRowUtilities:
    def test_merge_multiline_rows_regular(self) -> None:
        rows = [
            [
                "月",
                "1",
                "前期",
                "1",
                "ロボティクス",
                "佐藤 太郎",
                "smab020161",
                "22A",
                "対象[02機械]",
                "",
            ],
            ["", "", "", "", "特論", "鈴木 花子", "", "", "", ""],
        ]
        merged = merge_multiline_rows(rows, is_intensive=False)
        assert len(merged) == 1
        assert merged[0][4] == "ロボティクス特論"
        assert merged[0][5] == "佐藤 太郎\n鈴木 花子"

    def test_carry_forward_regular(self) -> None:
        rows = [
            ["月", "1", "前期", "1 一般", "科目A", "佐藤 太郎", "smab020161", "22A", "", ""],
            ["", "", "", "", "科目B", "鈴木 花子", "smab020162", "22B", "", ""],
        ]
        filled = carry_forward(rows, is_intensive=False)
        assert filled[1][0] == "月"
        assert filled[1][1] == "1"
        assert filled[1][2] == "前期"
        assert filled[1][3] == "1 一般"

    def test_merge_multiline_rows_intensive(self) -> None:
        rows = [
            ["前集中", "1", "データ科学", "佐藤 太郎", "smab020163", "22A", "対象[02機械]"],
            ["", "", "特論", "鈴木 花子", "", "", ""],
        ]
        merged = merge_multiline_rows(rows, is_intensive=True)
        assert len(merged) == 1
        assert merged[0][2] == "データ科学特論"
        assert merged[0][3] == "佐藤 太郎\n鈴木 花子"


class TestParseRegularRow:
    def test_valid_10_column_row(self) -> None:
        row = [
            "月",
            "1",
            "前期",
            "2 一般",
            "機械学習特論",
            "佐藤 太郎",
            "smab020164",
            "22A",
            "対象[02機械]",
            "備考あり",
        ]
        course = parse_regular_row(row)
        assert course is not None
        assert course.code == "smab020164"
        assert course.name == "機械学習特論"
        assert course.instructors == ["佐藤 太郎"]
        assert course.year_level == 2
        assert course.class_section == "一般"
        assert len(course.schedules) == 1
        assert course.schedules[0] == Schedule(term="前期", day="月", period=1, room="22A")

    def test_less_than_10_columns_returns_none(self) -> None:
        row = ["月", "1", "前期", "1", "科目", "教員", "smab020165", "22A", "対象[02機械]"]
        assert parse_regular_row(row) is None

    def test_invalid_course_code_returns_none(self) -> None:
        row = [
            "月",
            "1",
            "前期",
            "1",
            "科目",
            "教員",
            "invalid",
            "22A",
            "対象[02機械]",
            "",
        ]
        assert parse_regular_row(row) is None

    def test_row_with_paired_slots(self) -> None:
        row = [
            "月",
            "1",
            "前期後",
            "1",
            "ロボティクス特論",
            "佐藤 大祐",
            "smab020161",
            "22A",
            "対象[02機械]",
            "対開講(月1,木1)",
        ]
        course = parse_regular_row(row)
        assert course is not None
        assert len(course.schedules) == 2
        assert any(s.day == "月" and s.period == 1 and s.room == "22A" for s in course.schedules)
        assert any(s.day == "木" and s.period == 1 for s in course.schedules)
        assert course.notes == ""


class TestParseIntensiveRow:
    def test_valid_7_column_row(self) -> None:
        row = [
            "前集中",
            "1 一般",
            "集中講義",
            "佐藤 太郎",
            "smab020166",
            "22A",
            "対象[09情報]",
        ]
        course = parse_intensive_row(row)
        assert course is not None
        assert course.code == "smab020166"
        assert course.schedules == []
        assert course.targets == [CourseTarget(target_code="09", target_name="情報")]

    def test_less_than_7_columns_returns_none(self) -> None:
        row = ["前集中", "1", "集中講義", "佐藤 太郎", "smab020166", "22A"]
        assert parse_intensive_row(row) is None


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


class TestExtractCoursesFromPdfIntegration:
    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / "References" / "grad_timetable_front.pdf").exists(),
        reason="Reference PDF not found",
    )
    def test_extract_courses_from_reference_pdf(self, reference_pdf_path: Path) -> None:
        pdf_bytes = reference_pdf_path.read_bytes()
        courses = extract_courses_from_pdf(pdf_bytes)

        assert len(courses) > 150
        codes = {course.code for course in courses}
        assert "smab020161" in codes
        assert "smaa000031" in codes
        assert "smab000091" in codes

        target = next(course for course in courses if course.code == "smab020161")
        assert len(target.schedules) == 2
