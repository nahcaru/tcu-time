"""Tests for pipeline/advance.py (parse-only, no DB reflection)."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from ..advance import _request_course_names, extract_course_names


class TestRequestCourseNames:
    def test_valid_response(self) -> None:
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = json.dumps(["科目A", "科目B"])
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = _request_course_names("gemini-model", "test text")
            assert result == ["科目A", "科目B"]

    def test_response_text_none(self) -> None:
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = None
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Gemini response did not include text"):
                _request_course_names("gemini-model", "test text")

    def test_response_not_list(self) -> None:
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = json.dumps({"not": "a list"})
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Gemini JSON response must be a list"):
                _request_course_names("gemini-model", "test text")

    def test_response_list_non_strings(self) -> None:
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = json.dumps([1, 2, 3])
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Gemini JSON response must be a list of strings"):
                _request_course_names("gemini-model", "test text")


class TestExtractCourseNames:
    def test_extract_with_valid_pdf(self) -> None:
        """extract_course_names returns list[str] — no DB side effects."""
        pdf_bytes = b"test pdf content"
        with (
            patch("pipeline.advance.pdfplumber.open") as mock_open,
            patch("pipeline.advance._request_course_names") as mock_request,
            patch("pipeline.advance.Config") as mock_config,
        ):
            mock_config.GEMINI_MODEL = "primary-model"

            mock_page1 = Mock()
            mock_page1.extract_text.return_value = "Page 1 text"
            mock_page2 = Mock()
            mock_page2.extract_text.return_value = "Page 2 text"
            mock_pdf = Mock()
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdf.__enter__ = Mock(return_value=mock_pdf)
            mock_pdf.__exit__ = Mock(return_value=None)
            mock_open.return_value = mock_pdf
            mock_request.return_value = ["科目A", "科目B"]

            result = extract_course_names(pdf_bytes)

            assert result == ["科目A", "科目B"]
            mock_request.assert_called_once_with("primary-model", "Page 1 text\nPage 2 text")

    def test_extract_fallback_on_primary_failure(self) -> None:
        pdf_bytes = b"test pdf content"
        with (
            patch("pipeline.advance.pdfplumber.open") as mock_open,
            patch("pipeline.advance._request_course_names") as mock_request,
            patch("pipeline.advance.Config") as mock_config,
            patch("pipeline.advance.logger") as mock_logger,
        ):
            mock_config.GEMINI_MODEL = "primary-model"
            mock_config.GEMINI_FALLBACK_MODEL = "fallback-model"

            mock_page1 = Mock()
            mock_page1.extract_text.return_value = "Page 1 text"
            mock_pdf = Mock()
            mock_pdf.pages = [mock_page1]
            mock_pdf.__enter__ = Mock(return_value=mock_pdf)
            mock_pdf.__exit__ = Mock(return_value=None)
            mock_open.return_value = mock_pdf
            mock_request.side_effect = [Exception("Primary failed"), ["科目C", "科目D"]]

            result = extract_course_names(pdf_bytes)

            assert result == ["科目C", "科目D"]
            assert mock_request.call_count == 2
            mock_logger.warning.assert_called_once()

    def test_extract_empty_pdf_still_calls_gemini(self) -> None:
        pdf_bytes = b"test pdf content"
        with (
            patch("pipeline.advance.pdfplumber.open") as mock_open,
            patch("pipeline.advance._request_course_names") as mock_request,
            patch("pipeline.advance.Config") as mock_config,
        ):
            mock_config.GEMINI_MODEL = "primary-model"

            mock_page = Mock()
            mock_page.extract_text.return_value = None
            mock_pdf = Mock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = Mock(return_value=mock_pdf)
            mock_pdf.__exit__ = Mock(return_value=None)
            mock_open.return_value = mock_pdf
            mock_request.return_value = ["科目E"]

            result = extract_course_names(pdf_bytes)

            assert result == ["科目E"]
            mock_request.assert_called_once_with("primary-model", "")
