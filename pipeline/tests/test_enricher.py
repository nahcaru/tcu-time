from pipeline.models import CourseMetadata


class TestCourseMetadata:
    def test_valid_metadata(self) -> None:
        meta = CourseMetadata(
            curriculum_code="sm25091",
            category="専門",
            compulsoriness="選択",
            credits=2.0,
            syllabus_url="https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do?value(kougicd)=smab020161",
        )
        assert meta.credits == 2.0
        assert meta.category == "専門"

    def test_partial_metadata(self) -> None:
        meta = CourseMetadata(curriculum_code="sm25091")
        assert meta.category is None
        assert meta.credits is None
