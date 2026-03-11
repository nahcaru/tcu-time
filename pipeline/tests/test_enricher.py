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
    scrape_syllabus,
    enrich_courses,
    SyllabusFields,
)


class TestCourseMetadata:
    def test_valid_metadata(self) -> None:
        meta = CourseMetadata(
            curriculum_code="default",
            category="専門",
            credits=2.0,
        )
        assert meta.credits == 2.0
        assert meta.category == "専門"

    def test_partial_metadata(self) -> None:
        meta = CourseMetadata(curriculum_code="default")
        assert meta.category is None
        assert meta.credits is None


# =============================================================================
# Test build_syllabus_url()
# =============================================================================


class TestBuildSyllabusUrl:
    """Test URL building logic."""

    def test_basic_url(self) -> None:
        """URL should contain year and course code."""
        url = build_syllabus_url(year=2025, course_code="smab020161")
        assert "crclumcd" not in url
        assert "value(risyunen)=2025" in url
        assert "value(kougicd)=smab020161" in url


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
        category: str = "専門", credits: str = "2"
    ) -> str:
        """Minimal undergrad format HTML."""
        return f"""
        <table class="syllabus_detail">
            <tr>
                <td class="label_kougi">分野系列</td>
                <td class="line_y_label"></td>
                <td class="kougi">[{category}・選択]&nbsp;</td>
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
        """Grad school format: ■授業科目■ → category only."""
        html = self._grad_school_html(category="授業科目")
        fields = parse_syllabus_html(html)

        assert fields.category == "授業科目"
        assert fields.credits == 2.0

    def test_undergrad_format(self) -> None:
        """Undergrad format: [専門・選択] → category extracted."""
        html = self._undergrad_html(category="専門")
        fields = parse_syllabus_html(html)

        assert fields.category == "専門"
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
        assert fields.credits is None

    def test_empty_html(self) -> None:
        """Empty/minimal HTML should return empty SyllabusFields."""
        html = ""
        fields = parse_syllabus_html(html)

        assert fields.category is None
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

        result = scrape_syllabus(year=2025, course_code="smab020161")

        assert result is not None
        assert result.category == "授業科目"
        assert result.credits == 3.0
        assert result.curriculum_code == "default"

    @patch("pipeline.enricher.fetch_syllabus_page")
    def test_fetch_returns_none(self, mock_fetch: Mock) -> None:
        """When fetch returns None, scrape_syllabus should return None."""
        mock_fetch.return_value = None

        result = scrape_syllabus(year=2025, course_code="smab020161")

        assert result is None

    @patch("pipeline.enricher.fetch_syllabus_page")
    def test_default_curriculum_code(self, mock_fetch: Mock) -> None:
        """Should always use 'default' curriculum code."""
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
        success, failure = enrich_courses([], academic_year=2025)

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

        success, failure = enrich_courses(courses, academic_year=2025)

        assert success == 2
        assert failure == 0
        assert mock_scrape.call_count == 2
        assert mock_upsert.call_count == 2
        assert mock_sleep.call_count == 1  # sleep between courses

    @patch("pipeline.enricher.db.upsert_metadata")
    @patch("pipeline.enricher.scrape_syllabus")
    @patch("pipeline.enricher.time.sleep")
    def test_one_course_scrape_fails(
        self, mock_sleep: Mock, mock_scrape: Mock, mock_upsert: Mock
    ) -> None:
        """When scrape fails, should return (0, 1)."""
        courses = [{"id": "1", "code": "smab020161", "name": "Course 1"}]

        mock_scrape.return_value = None

        success, failure = enrich_courses(courses, academic_year=2025)

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

        success, failure = enrich_courses(courses, academic_year=2025)

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

        success, failure = enrich_courses(courses, academic_year=2025)

        assert success == 1
        assert failure == 1
        assert mock_scrape.call_count == 2
        assert mock_upsert.call_count == 1
