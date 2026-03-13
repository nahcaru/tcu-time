from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from ..classifier import (
    _build_prompt,
    _request_classification,
    classify_pages,
    get_course_table_pages,
)
from ..models import PageClassification, PageType


class TestBuildPrompt:
    def test_returns_string_with_input_and_categories(self) -> None:
        """Should return a string containing input JSON and classification categories."""
        json_str = '[{"page": 1, "has_table": false}]'
        result = _build_prompt(json_str)
        
        assert isinstance(result, str)
        assert json_str in result
        assert "course_table_spring" in result
        assert "course_table_fall" in result
        assert "cover" in result
        assert "notes" in result
        assert "schedule" in result
        assert "map" in result
        assert "manual" in result
        assert "other" in result

    def test_prompt_includes_table_header_instruction(self) -> None:
        """Should include instruction about extracting table headers."""
        json_str = '[{"page": 1}]'
        result = _build_prompt(json_str)
        
        assert "ヘッダー" in result or "headers" in result


class TestRequestClassification:
    @patch("pipeline.classifier.genai")
    def test_valid_json_list_returns_classifications(self, mock_genai: Mock) -> None:
        """Should parse valid JSON list and return PageClassification objects."""
        mock_response = Mock()
        mock_response.text = '[{"page": 1, "type": "cover", "headers": null}]'
        
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        mock_genai.types.GenerateContentConfig = Mock()
        
        result = _request_classification("gemini-test", "test prompt")
        
        assert len(result) == 1
        assert isinstance(result[0], PageClassification)
        assert result[0].page == 1
        assert result[0].type == "cover"
        assert result[0].headers is None

    @patch("pipeline.classifier.genai")
    def test_multiple_classifications(self, mock_genai: Mock) -> None:
        """Should handle multiple page classifications."""
        mock_response = Mock()
        mock_response.text = '''[
            {"page": 1, "type": "cover", "headers": null},
            {"page": 2, "type": "course_table_spring", "headers": ["曜", "限"]},
            {"page": 3, "type": "notes", "headers": null}
        ]'''
        
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        mock_genai.types.GenerateContentConfig = Mock()
        
        result = _request_classification("gemini-test", "test prompt")
        
        assert len(result) == 3
        assert result[0].type == "cover"
        assert result[1].type == "course_table_spring"
        assert result[1].headers == ["曜", "限"]
        assert result[2].type == "notes"

    @patch("pipeline.classifier.genai")
    def test_empty_response_text_raises_error(self, mock_genai: Mock) -> None:
        """Should raise ValueError when response.text is empty."""
        mock_response = Mock()
        mock_response.text = ""
        
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        mock_genai.types.GenerateContentConfig = Mock()
        
        with pytest.raises(ValueError, match="Gemini response did not include text"):
            _request_classification("gemini-test", "test prompt")

    @patch("pipeline.classifier.genai")
    def test_non_list_json_raises_error(self, mock_genai: Mock) -> None:
        """Should raise ValueError when JSON is not a list."""
        mock_response = Mock()
        mock_response.text = '{"page": 1, "type": "cover"}'
        
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        mock_genai.types.GenerateContentConfig = Mock()
        
        with pytest.raises(ValueError, match="Gemini JSON response must be a list"):
            _request_classification("gemini-test", "test prompt")

    @patch("pipeline.classifier.genai")
    def test_calls_genai_with_correct_params(self, mock_genai: Mock) -> None:
        """Should call genai.Client with correct parameters."""
        mock_response = Mock()
        mock_response.text = '[]'
        
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        mock_genai.types.GenerateContentConfig = Mock()
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_API_KEY = "test-key"
            _request_classification("gemini-model", "test prompt")
        
        mock_genai.Client.assert_called_once()


class TestClassifyPages:
    def _create_mock_page(self, text: str, has_tables: bool = False) -> Mock:
        """Helper to create a mock pdfplumber page."""
        mock_page = Mock()
        mock_page.extract_text.return_value = text
        mock_page.extract_tables.return_value = [
            [["Col1", "Col2"], ["val1", "val2"]]
        ] if has_tables else []
        return mock_page

    @patch("pipeline.classifier._request_classification")
    @patch("pipeline.classifier.pdfplumber")
    def test_classify_pages_basic(
        self, mock_pdfplumber: Mock, mock_request: Mock
    ) -> None:
        """Should extract pages and request classification."""
        pdf_bytes = b"fake pdf"
        
        mock_page1 = self._create_mock_page("Cover page", has_tables=False)
        mock_page2 = self._create_mock_page("Monday Tuesday Wednesday", has_tables=True)
        mock_page3 = self._create_mock_page("Important notes", has_tables=False)
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        classifications = [
            PageClassification(page=1, type="cover"),
            PageClassification(page=2, type="course_table_spring", headers=["曜", "限"]),
            PageClassification(page=3, type="notes"),
        ]
        mock_request.return_value = classifications
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_MODEL = "gemini-model"
            result = classify_pages(pdf_bytes)
        
        assert len(result) == 3
        assert result[0].page == 1
        assert result[1].page == 2
        assert result[2].page == 3

    @patch("pipeline.classifier._request_classification")
    @patch("pipeline.classifier.pdfplumber")
    def test_classify_pages_with_table_column_count(
        self, mock_pdfplumber: Mock, mock_request: Mock
    ) -> None:
        """Should extract table column counts."""
        pdf_bytes = b"fake pdf"
        
        mock_page = Mock()
        mock_page.extract_text.return_value = "Table content"
        mock_page.extract_tables.return_value = [
            [["H1", "H2", "H3"], ["v1", "v2", "v3"]]
        ]
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        mock_request.return_value = [
            PageClassification(page=1, type="course_table_spring")
        ]
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_MODEL = "gemini-model"
            classify_pages(pdf_bytes)
        
        # Verify _request_classification was called with a prompt containing summaries
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        prompt = call_args[0][1]
        assert "has_table" in prompt
        assert "col_count" in prompt

    @patch("pipeline.classifier._request_classification")
    @patch("pipeline.classifier.pdfplumber")
    def test_classify_pages_fallback_on_primary_error(
        self, mock_pdfplumber: Mock, mock_request: Mock
    ) -> None:
        """Should try fallback model when primary model raises."""
        pdf_bytes = b"fake pdf"
        
        mock_page = self._create_mock_page("Test content")
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        fallback_result = [PageClassification(page=1, type="other")]
        mock_request.side_effect = [
            ValueError("Primary model error"),
            fallback_result,
        ]
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_MODEL = "primary-model"
            mock_config.GEMINI_FALLBACK_MODEL = "fallback-model"
            result = classify_pages(pdf_bytes)
        
        assert result == fallback_result
        assert mock_request.call_count == 2
        assert mock_request.call_args_list[0][0][0] == "primary-model"
        assert mock_request.call_args_list[1][0][0] == "fallback-model"

    @patch("pipeline.classifier._request_classification")
    @patch("pipeline.classifier.pdfplumber")
    def test_classify_pages_fallback_on_json_decode_error(
        self, mock_pdfplumber: Mock, mock_request: Mock
    ) -> None:
        """Should try fallback when JSONDecodeError occurs."""
        pdf_bytes = b"fake pdf"
        
        mock_page = self._create_mock_page("Test content")
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        fallback_result = [PageClassification(page=1, type="cover")]
        mock_request.side_effect = [
            ValueError("JSON error"),
            fallback_result,
        ]
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_MODEL = "primary-model"
            mock_config.GEMINI_FALLBACK_MODEL = "fallback-model"
            result = classify_pages(pdf_bytes)
        
        assert result == fallback_result
        assert mock_request.call_count == 2

    @patch("pipeline.classifier._request_classification")
    @patch("pipeline.classifier.pdfplumber")
    def test_classify_pages_truncates_text_to_300_chars(
        self, mock_pdfplumber: Mock, mock_request: Mock
    ) -> None:
        """Should truncate page text to 300 characters in summary."""
        pdf_bytes = b"fake pdf"
        
        long_text = "a" * 500
        mock_page = self._create_mock_page(long_text)
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        mock_request.return_value = [PageClassification(page=1, type="other")]
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_MODEL = "gemini-model"
            classify_pages(pdf_bytes)
        
        call_args = mock_request.call_args
        prompt = call_args[0][1]
        assert "a" * 300 in prompt
        assert "a" * 301 not in prompt

    @patch("pipeline.classifier._request_classification")
    @patch("pipeline.classifier.pdfplumber")
    def test_classify_pages_handles_none_text(
        self, mock_pdfplumber: Mock, mock_request: Mock
    ) -> None:
        """Should handle pages with None text (empty string fallback)."""
        pdf_bytes = b"fake pdf"
        
        mock_page = Mock()
        mock_page.extract_text.return_value = None
        mock_page.extract_tables.return_value = []
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        mock_request.return_value = [PageClassification(page=1, type="other")]
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_MODEL = "gemini-model"
            result = classify_pages(pdf_bytes)
        
        assert len(result) == 1
        mock_request.assert_called_once()

    @patch("pipeline.classifier._request_classification")
    @patch("pipeline.classifier.pdfplumber")
    def test_classify_pages_uses_bytesio_wrapper(
        self, mock_pdfplumber: Mock, mock_request: Mock
    ) -> None:
        """Should wrap pdf_bytes in BytesIO when opening."""
        pdf_bytes = b"fake pdf content"
        
        mock_page = self._create_mock_page("content")
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        mock_request.return_value = []
        
        with patch("pipeline.classifier.Config") as mock_config:
            mock_config.GEMINI_MODEL = "gemini-model"
            classify_pages(pdf_bytes)
        
        # Verify pdfplumber.open was called with BytesIO
        call_args = mock_pdfplumber.open.call_args[0][0]
        assert isinstance(call_args, BytesIO)


class TestGetCourseTablePages:
    def test_filters_course_table_spring(self) -> None:
        """Should include course_table_spring pages."""
        classifications = [
            PageClassification(page=1, type="cover"),
            PageClassification(page=2, type="course_table_spring"),
            PageClassification(page=3, type="notes"),
        ]
        
        result = get_course_table_pages(classifications)
        
        assert len(result) == 1
        assert result[0].page == 2
        assert result[0].type == "course_table_spring"

    def test_filters_course_table_fall(self) -> None:
        """Should include course_table_fall pages."""
        classifications = [
            PageClassification(page=1, type="cover"),
            PageClassification(page=2, type="course_table_fall"),
            PageClassification(page=3, type="notes"),
        ]
        
        result = get_course_table_pages(classifications)
        
        assert len(result) == 1
        assert result[0].page == 2
        assert result[0].type == "course_table_fall"

    def test_filters_both_course_tables(self) -> None:
        """Should include both spring and fall course tables."""
        classifications = [
            PageClassification(page=1, type="cover"),
            PageClassification(page=2, type="course_table_spring"),
            PageClassification(page=3, type="course_table_fall"),
            PageClassification(page=4, type="notes"),
        ]
        
        result = get_course_table_pages(classifications)
        
        assert len(result) == 2
        assert result[0].type == "course_table_spring"
        assert result[1].type == "course_table_fall"

    def test_excludes_non_course_table_types(self) -> None:
        """Should exclude cover, notes, schedule, map, manual, other."""
        classifications = [
            PageClassification(page=1, type="cover"),
            PageClassification(page=2, type="notes"),
            PageClassification(page=3, type="schedule"),
            PageClassification(page=4, type="map"),
            PageClassification(page=5, type="manual"),
            PageClassification(page=6, type="other"),
        ]
        
        result = get_course_table_pages(classifications)
        
        assert len(result) == 0

    def test_empty_list(self) -> None:
        """Should return empty list when given empty input."""
        result = get_course_table_pages([])
        
        assert result == []

    def test_preserves_headers(self) -> None:
        """Should preserve headers in filtered results."""
        classifications = [
            PageClassification(
                page=1,
                type="course_table_spring",
                headers=["曜", "限", "科目"],
            ),
            PageClassification(page=2, type="cover"),
        ]
        
        result = get_course_table_pages(classifications)
        
        assert len(result) == 1
        assert result[0].headers == ["曜", "限", "科目"]

    def test_mixed_pages_with_and_without_headers(self) -> None:
        """Should handle mix of course tables with and without headers."""
        classifications = [
            PageClassification(page=1, type="course_table_spring", headers=["曜"]),
            PageClassification(page=2, type="course_table_fall", headers=None),
            PageClassification(page=3, type="notes"),
        ]
        
        result = get_course_table_pages(classifications)
        
        assert len(result) == 2
        assert result[0].headers == ["曜"]
        assert result[1].headers is None
