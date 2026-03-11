from pipeline.models import ExtractedCourse, Schedule, CourseTarget


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
