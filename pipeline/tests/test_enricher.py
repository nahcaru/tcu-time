import re
import unittest
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from ..models import CourseMetadata
from ..enricher import (
    build_syllabus_url,
    parse_syllabus_html,
    _find_label_value,
    fetch_syllabus_page,
    fetch_curriculum_codes,
    get_curriculum_codes_for_year,
    match_curriculum_codes,
    scrape_syllabus,
    enrich_courses,
    SyllabusFields,
)


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


# =============================================================================
# Test build_syllabus_url()
# =============================================================================


class TestBuildSyllabusUrl:
    """Test URL building logic."""

    def test_without_curriculum_code(self) -> None:
        """URL should not have crclumcd param when curriculum_code is None."""
        url = build_syllabus_url(year=2025, course_code="smab020161")
        assert "crclumcd" not in url
        assert "value(risyunen)=2025" in url
        assert "value(kougicd)=smab020161" in url

    def test_with_curriculum_code(self) -> None:
        """URL should include crclumcd param when curriculum_code is provided."""
        url = build_syllabus_url(
            year=2025, course_code="smab020161", curriculum_code="s24310"
        )
        assert "value(crclumcd)=s24310" in url
        assert "value(risyunen)=2025" in url

    def test_with_default_curriculum_code(self) -> None:
        """URL should not have crclumcd param when curriculum_code is 'default'."""
        url = build_syllabus_url(
            year=2025,
            course_code="smab020161",
            curriculum_code="default",
        )
        assert "crclumcd" not in url
        assert "value(risyunen)=2025" in url


# =============================================================================
# Test _find_label_value()
# =============================================================================


class TestFindLabelValue:
    """Test HTML label-value finding logic."""

    @staticmethod
    def _make_row_with_label_value(label_text: str, value_text: str):
        """Helper to create a mock row with label and value cells."""
        from bs4 import BeautifulSoup

        html = f"""
        <tr>
            <td class="label_kougi">{label_text}</td>
            <td class="line_y_label"></td>
            <td class="kougi">{value_text}&nbsp;</td>
        </tr>
        """
        soup = BeautifulSoup(html, "html.parser")
        return soup.find("tr")

    def test_finds_known_label(self) -> None:
        """Should find the correct value for a known label."""
        from bs4 import BeautifulSoup, Tag

        row = self._make_row_with_label_value("単位数<BR>/Number", "2")
        rows = [row] if row else []

        result = _find_label_value(rows, "単位数")
        assert result == "2"

    def test_returns_none_for_missing_label(self) -> None:
        """Should return None for a non-existent label."""
        from bs4 import BeautifulSoup, Tag

        row = self._make_row_with_label_value("単位数<BR>/Number", "2")
        rows = [row] if row else []

        result = _find_label_value(rows, "nonexistent")
        assert result is None

    def test_strips_nbsp(self) -> None:
        """Should strip non-breaking spaces from values."""
        from bs4 import BeautifulSoup, Tag

        row = self._make_row_with_label_value("単位数", "2.5&nbsp;")
        rows = [row] if row else []

        result = _find_label_value(rows, "単位数")
        assert result == "2.5"


# =============================================================================
# Test parse_syllabus_html()
# =============================================================================


class TestParseSyllabusHtml:
    """Test HTML parsing logic."""

    @staticmethod
    def _grad_school_html(category: str = "授業科目", credits: str = "2") -> str:
        """Minimal grad school format HTML."""
        return f"""
        <table class="syllabus_detail">
            <tr>
                <td class="label_kougi">分野系列<BR>/Subject Category</td>
                <td class="line_y_label"></td>
                <td class="kougi">■{category}■&nbsp;</td>
            </tr>
            <tr><td class="line_x" colspan="3"></td></tr>
            <tr>
                <td class="label_kougi">単位数<BR>/Number of Credit(s)</td>
                <td class="line_y_label"></td>
                <td class="kougi">{credits}&nbsp;</td>
            </tr>
        </table>
        """

    @staticmethod
    def _undergrad_html(
        category: str = "専門", compulsoriness: str = "選択", credits: str = "2"
    ) -> str:
        """Minimal undergrad format HTML."""
        return f"""
        <table class="syllabus_detail">
            <tr>
                <td class="label_kougi">分野系列</td>
                <td class="line_y_label"></td>
                <td class="kougi">[{category}・{compulsoriness}]&nbsp;</td>
            </tr>
            <tr><td class="line_x" colspan="3"></td></tr>
            <tr>
                <td class="label_kougi">単位数</td>
                <td class="line_y_label"></td>
                <td class="kougi">{credits}&nbsp;</td>
            </tr>
        </table>
        """

    def test_grad_school_format(self) -> None:
        """Grad school format: ■授業科目■ → category, no compulsoriness."""
        html = self._grad_school_html(category="授業科目")
        fields = parse_syllabus_html(html)

        assert fields.category == "授業科目"
        assert fields.compulsoriness is None
        assert fields.credits == 2.0

    def test_undergrad_format(self) -> None:
        """Undergrad format: [専門・選択] → category and compulsoriness."""
        html = self._undergrad_html(category="専門", compulsoriness="選択")
        fields = parse_syllabus_html(html)

        assert fields.category == "専門"
        assert fields.compulsoriness == "選択"
        assert fields.credits == 2.0

    def test_credits_parsing_integer(self) -> None:
        """Credits "2" should parse as 2.0."""
        html = self._grad_school_html(credits="2")
        fields = parse_syllabus_html(html)

        assert fields.credits == 2.0

    def test_credits_parsing_float(self) -> None:
        """Credits "0.5" should parse as 0.5."""
        html = self._grad_school_html(credits="0.5")
        fields = parse_syllabus_html(html)

        assert fields.credits == 0.5

    def test_missing_syllabus_detail_table(self) -> None:
        """Missing syllabus_detail table should return empty SyllabusFields."""
        html = "<html><body><h1>No table here</h1></body></html>"
        fields = parse_syllabus_html(html)

        assert fields.category is None
        assert fields.compulsoriness is None
        assert fields.credits is None

    def test_empty_html(self) -> None:
        """Empty/minimal HTML should return empty SyllabusFields."""
        html = ""
        fields = parse_syllabus_html(html)

        assert fields.category is None
        assert fields.compulsoriness is None
        assert fields.credits is None

    def test_fallback_category_text(self) -> None:
        """Category text without markers should use raw text."""
        html = """
        <table class="syllabus_detail">
            <tr>
                <td class="label_kougi">分野系列</td>
                <td class="line_y_label"></td>
                <td class="kougi">共通科目</td>
            </tr>
        </table>
        """
        fields = parse_syllabus_html(html)

        assert fields.category == "共通科目"
        assert fields.compulsoriness is None


# =============================================================================
# Test fetch_syllabus_page()
# =============================================================================


class TestFetchSyllabusPage:
    """Test HTTP fetching logic."""

    @patch("pipeline.enricher._get_shared_session")
    def test_successful_response(self, mock_get_session: Mock) -> None:
        """Successful response should return HTML string."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test HTML</body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = fetch_syllabus_page("https://example.com/syllabus")

        assert result == "<html><body>Test HTML</body></html>"
        mock_session.get.assert_called_once()

    @patch("pipeline.enricher._get_shared_session")
    def test_http_error_500(self, mock_get_session: Mock) -> None:
        """HTTP error (status 500) should return None."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error"
        )
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = fetch_syllabus_page("https://example.com/syllabus")

        assert result is None

    @patch("pipeline.enricher._get_shared_session")
    def test_connection_error(self, mock_get_session: Mock) -> None:
        """Network error (ConnectionError) should return None."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.ConnectionError("Connection failed")
        mock_get_session.return_value = mock_session

        result = fetch_syllabus_page("https://example.com/syllabus")

        assert result is None


class TestFetchCurriculumCodes:
    @patch("pipeline.enricher._get_shared_session")
    def test_successful_fetch(self, mock_get_session: Mock) -> None:
        html = """
        <a href="slbsscmr.do?value(crclm)=sm250101&buttonName=search">2025年度 機械専攻(機械工学)</a>
        <a href="slbsscmr.do?value(crclm)=sd250101&buttonName=search">2025年度 博士課程</a>
        """
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = fetch_curriculum_codes()

        assert result == {
            "sm250101": "2025年度 機械専攻(機械工学)",
            "sd250101": "2025年度 博士課程",
        }

    @patch("pipeline.enricher._get_shared_session")
    def test_fetch_error_returns_empty(self, mock_get_session: Mock) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.RequestException("boom")
        mock_get_session.return_value = mock_session

        assert fetch_curriculum_codes() == {}

    @patch("pipeline.enricher._get_shared_session")
    def test_regex_handles_amp_entity(self, mock_get_session: Mock) -> None:
        html = """
        <a href="slbsscmr.do?value(crclm)=sm250201&buttonName=search">2025年度 A</a>
        <a href="slbsscmr.do?value(crclm)=sm250301&amp;buttonName=search">2025年度 B</a>
        """
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        result = fetch_curriculum_codes()

        assert result["sm250201"] == "2025年度 A"
        assert result["sm250301"] == "2025年度 B"


class TestGetCurriculumCodesForYear:
    def test_filters_by_year(self) -> None:
        all_codes = {
            "sm250101": "2025 M1",
            "sd250101": "2025 D1",
            "sm240101": "2024 M1",
        }

        result = get_curriculum_codes_for_year(all_codes, 2025)

        assert result == {
            "sm250101": "2025 M1",
            "sd250101": "2025 D1",
        }

    def test_empty_input(self) -> None:
        assert get_curriculum_codes_for_year({}, 2025) == {}


class TestMatchCurriculumCodes:
    def test_basic_matching(self) -> None:
        curriculum_codes = {
            "sm250201": "機械システム",
            "sm250901": "情報工学",
        }
        assert match_curriculum_codes(["02"], curriculum_codes) == ["sm250201"]

    def test_single_digit_target_code(self) -> None:
        curriculum_codes = {
            "sm250701": "建築学",
            "sm250801": "都市工学",
        }
        assert match_curriculum_codes(["7"], curriculum_codes) == ["sm250701"]

    def test_common_target_matches_all(self) -> None:
        curriculum_codes = {
            "sm250201": "機械システム",
            "sm250901": "情報工学",
        }
        assert match_curriculum_codes(["00"], curriculum_codes) == sorted(
            curriculum_codes.keys()
        )

    def test_common_single_zero(self) -> None:
        curriculum_codes = {
            "sm250201": "機械システム",
            "sm250901": "情報工学",
        }
        assert match_curriculum_codes(["0"], curriculum_codes) == sorted(
            curriculum_codes.keys()
        )

    def test_no_match(self) -> None:
        curriculum_codes = {
            "sm250201": "機械システム",
            "sm250901": "情報工学",
        }
        assert match_curriculum_codes(["99"], curriculum_codes) == []

    def test_multiple_targets(self) -> None:
        curriculum_codes = {
            "sm250201": "機械システム",
            "sm250701": "建築学",
            "sm250901": "情報工学",
        }
        assert match_curriculum_codes(["02", "07"], curriculum_codes) == [
            "sm250201",
            "sm250701",
        ]


# =============================================================================
# Test scrape_syllabus()
# =============================================================================


class TestScrapeSyllabus:
    """Test high-level syllabus scraping."""

    @patch("pipeline.enricher.fetch_syllabus_page")
    def test_successful_scrape(self, mock_fetch: Mock) -> None:
        """Successful scrape should return CourseMetadata with correct fields."""
        html = """
        <table class="syllabus_detail">
            <tr>
                <td class="label_kougi">分野系列</td>
                <td class="line_y_label"></td>
                <td class="kougi">■授業科目■&nbsp;</td>
            </tr>
            <tr>
                <td class="label_kougi">単位数</td>
                <td class="line_y_label"></td>
                <td class="kougi">3&nbsp;</td>
            </tr>
        </table>
        """
        mock_fetch.return_value = html

        result = scrape_syllabus(
            year=2025, course_code="smab020161", curriculum_code="s24310"
        )

        assert result is not None
        assert result.category == "授業科目"
        assert result.credits == 3.0
        assert result.curriculum_code == "s24310"
        assert "smab020161" in result.syllabus_url

    @patch("pipeline.enricher.fetch_syllabus_page")
    def test_fetch_returns_none(self, mock_fetch: Mock) -> None:
        """When fetch returns None, scrape_syllabus should return None."""
        mock_fetch.return_value = None

        result = scrape_syllabus(year=2025, course_code="smab020161")

        assert result is None

    @patch("pipeline.enricher.fetch_syllabus_page")
    def test_syllabus_url_set_correctly(self, mock_fetch: Mock) -> None:
        """Syllabus URL should be set correctly on returned metadata."""
        mock_fetch.return_value = "<table class='syllabus_detail'></table>"

        result = scrape_syllabus(year=2025, course_code="smab020161")

        assert result is not None
        assert "smab020161" in result.syllabus_url
        assert "value(risyunen)=2025" in result.syllabus_url

    @patch("pipeline.enricher.fetch_syllabus_page")
    def test_default_curriculum_code(self, mock_fetch: Mock) -> None:
        """When curriculum_code is None, should use 'default'."""
        mock_fetch.return_value = "<table class='syllabus_detail'></table>"

        result = scrape_syllabus(year=2025, course_code="smab020161")

        assert result is not None
        assert result.curriculum_code == "default"


# =============================================================================
# Test enrich_courses()
# =============================================================================


class TestEnrichCourses:
    """Test main enrichment orchestration."""

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_empty_course_list(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        """Empty course list should return (0, 0)."""
        success, failure = enrich_courses([], academic_year=2025, curriculum_codes={})

        assert success == 0
        assert failure == 0
        mock_scrape.assert_not_called()
        mock_upsert.assert_not_called()

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_two_courses_both_succeed(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        """Two courses, both succeeding, should return (2, 0)."""
        courses = [
            {"id": "1", "code": "smab020161", "name": "Course 1"},
            {"id": "2", "code": "smcd030001", "name": "Course 2"},
        ]

        # Create mock metadata for each course
        meta1 = CourseMetadata(
            curriculum_code="default", category="授業科目", credits=2.0
        )
        meta2 = CourseMetadata(
            curriculum_code="default", category="専門", credits=3.0
        )
        mock_scrape.side_effect = [meta1, meta2]

        success, failure = enrich_courses(courses, academic_year=2025, curriculum_codes={})

        assert success == 2
        assert failure == 0
        assert mock_scrape.call_count == 2
        assert mock_upsert.call_count == 2
        assert mock_sleep.call_count == 1  # 2 courses - 1

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_one_course_scrape_fails(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        """When scrape fails, should return (0, 1)."""
        courses = [{"id": "1", "code": "smab020161", "name": "Course 1"}]

        mock_scrape.return_value = None

        success, failure = enrich_courses(courses, academic_year=2025, curriculum_codes={})

        assert success == 0
        assert failure == 1
        mock_scrape.assert_called_once()
        mock_upsert.assert_not_called()

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_scrape_succeeds_db_upsert_fails(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        """When scrape succeeds but DB upsert raises, should return (0, 1)."""
        courses = [{"id": "1", "code": "smab020161", "name": "Course 1"}]

        meta = CourseMetadata(
            curriculum_code="default", category="授業科目", credits=2.0
        )
        mock_scrape.return_value = meta
        mock_upsert.side_effect = Exception("DB error")

        success, failure = enrich_courses(courses, academic_year=2025, curriculum_codes={})

        assert success == 0
        assert failure == 1
        mock_scrape.assert_called_once()
        mock_upsert.assert_called_once()

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_mixed_success_and_failure(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        """Mixed results: 1 success, 1 failure should return (1, 1)."""
        courses = [
            {"id": "1", "code": "smab020161", "name": "Course 1"},
            {"id": "2", "code": "smcd030001", "name": "Course 2"},
        ]

        meta = CourseMetadata(
            curriculum_code="default", category="授業科目", credits=2.0
        )
        mock_scrape.side_effect = [meta, None]

        success, failure = enrich_courses(courses, academic_year=2025, curriculum_codes={})

        assert success == 1
        assert failure == 1
        assert mock_scrape.call_count == 2
        assert mock_upsert.call_count == 1

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_per_curriculum_enrichment(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        courses = [
            {
                "id": "1",
                "code": "smab020161",
                "name": "Course 1",
                "targets": [{"target_code": "02", "target_name": "機械"}],
            }
        ]
        curriculum_codes = {
            "sm250201": "機械専攻(機械システム)",
            "sm250901": "情報専攻(情報工学)",
        }
        mock_scrape.side_effect = [
            CourseMetadata(curriculum_code="sm250201", category="専門", credits=2.0),
            CourseMetadata(curriculum_code="default", category="授業科目", credits=2.0),
        ]

        success, failure = enrich_courses(
            courses,
            academic_year=2025,
            curriculum_codes=curriculum_codes,
        )

        assert success == 2
        assert failure == 0
        assert mock_scrape.call_args_list[0].kwargs["curriculum_code"] == "sm250201"
        assert mock_scrape.call_args_list[1].kwargs["curriculum_code"] is None
        assert mock_upsert.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_skips_already_enriched(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        courses = [
            {
                "id": "1",
                "code": "smab020161",
                "name": "Course 1",
                "targets": [{"target_code": "02", "target_name": "機械"}],
                "existing_metadata_codes": ["sm250201", "default"],
            }
        ]
        curriculum_codes = {"sm250201": "機械専攻(機械システム)"}

        success, failure = enrich_courses(
            courses,
            academic_year=2025,
            curriculum_codes=curriculum_codes,
        )

        assert success == 0
        assert failure == 0
        mock_scrape.assert_not_called()
        mock_upsert.assert_not_called()
        mock_sleep.assert_not_called()
