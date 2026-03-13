import json
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from ..advance import _request_course_names, extract_course_names, update_flags


class TestRequestCourseNames:
    def test_valid_response(self) -> None:
        """Should parse valid JSON array of course names."""
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = json.dumps(["科目A", "科目B"])
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = _request_course_names("gemini-model", "test text")

            assert result == ["科目A", "科目B"]
            mock_client_class.assert_called_once()

    def test_response_text_none(self) -> None:
        """Should raise ValueError when response.text is None."""
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = None
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Gemini response did not include text"):
                _request_course_names("gemini-model", "test text")

    def test_response_not_list(self) -> None:
        """Should raise ValueError when JSON is not a list."""
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = json.dumps({"not": "a list"})
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Gemini JSON response must be a list"):
                _request_course_names("gemini-model", "test text")

    def test_response_list_non_strings(self) -> None:
        """Should raise ValueError when list contains non-strings."""
        with patch("pipeline.advance.genai.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.text = json.dumps([1, 2, 3])
            mock_client = Mock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(
                ValueError, match="Gemini JSON response must be a list of strings"
            ):
                _request_course_names("gemini-model", "test text")


class TestExtractCourseNames:
    def test_extract_with_valid_pdf(self) -> None:
        """Should extract course names from PDF using primary model."""
        pdf_bytes = b"test pdf content"

        with patch("pipeline.advance.pdfplumber.open") as mock_open, patch(
            "pipeline.advance._request_course_names"
        ) as mock_request, patch("pipeline.advance.Config") as mock_config:
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
        """Should use fallback model when primary model fails."""
        pdf_bytes = b"test pdf content"

        with patch("pipeline.advance.pdfplumber.open") as mock_open, patch(
            "pipeline.advance._request_course_names"
        ) as mock_request, patch("pipeline.advance.Config") as mock_config, patch(
            "pipeline.advance.logger"
        ) as mock_logger:
            mock_config.GEMINI_MODEL = "primary-model"
            mock_config.GEMINI_FALLBACK_MODEL = "fallback-model"

            mock_page1 = Mock()
            mock_page1.extract_text.return_value = "Page 1 text"
            mock_pdf = Mock()
            mock_pdf.pages = [mock_page1]
            mock_pdf.__enter__ = Mock(return_value=mock_pdf)
            mock_pdf.__exit__ = Mock(return_value=None)
            mock_open.return_value = mock_pdf

            # Primary fails, fallback succeeds
            mock_request.side_effect = [
                Exception("Primary failed"),
                ["科目C", "科目D"],
            ]

            result = extract_course_names(pdf_bytes)

            assert result == ["科目C", "科目D"]
            assert mock_request.call_count == 2
            mock_logger.warning.assert_called_once()

    def test_extract_empty_pdf_still_calls_gemini(self) -> None:
        """Should still call Gemini even when PDF has no text."""
        pdf_bytes = b"test pdf content"

        with patch("pipeline.advance.pdfplumber.open") as mock_open, patch(
            "pipeline.advance._request_course_names"
        ) as mock_request, patch("pipeline.advance.Config") as mock_config:
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


class TestUpdateFlags:
    def test_update_with_matching_courses(self) -> None:
        """Should reset and set advance enrollment for matched courses."""
        course_names = ["科目A", "科目B", "科目C"]

        with patch("pipeline.advance.db") as mock_db, patch(
            "pipeline.advance.logger"
        ) as mock_logger:
            mock_db.reset_advance_enrollment.return_value = 5
            mock_db.find_courses_by_name.side_effect = [
                [{"id": 1}],  # 科目A matches 1 course
                [{"id": 2}, {"id": 3}],  # 科目B matches 2 courses
                [],  # 科目C has no match
            ]
            mock_db.set_advance_enrollment.return_value = {"id": 1}

            update_flags(course_names, 2024)

            mock_db.reset_advance_enrollment.assert_called_once_with(2024)
            assert mock_db.set_advance_enrollment.call_count == 3
            mock_logger.warning.assert_called_once()
            mock_logger.info.assert_called_once()

    def test_update_with_empty_course_names(self) -> None:
        """Should reset enrollment but not update any courses for empty list."""
        course_names: list[str] = []

        with patch("pipeline.advance.db") as mock_db, patch(
            "pipeline.advance.logger"
        ) as mock_logger:
            mock_db.reset_advance_enrollment.return_value = 3

            update_flags(course_names, 2024)

            mock_db.reset_advance_enrollment.assert_called_once_with(2024)
            mock_db.find_courses_by_name.assert_not_called()
            mock_db.set_advance_enrollment.assert_not_called()
            mock_logger.info.assert_called_once()

    def test_update_multiple_courses_per_name(self) -> None:
        """Should handle case where one name matches multiple courses."""
        course_names = ["科目A"]

        with patch("pipeline.advance.db") as mock_db, patch(
            "pipeline.advance.logger"
        ) as mock_logger:
            mock_db.reset_advance_enrollment.return_value = 0
            mock_db.find_courses_by_name.return_value = [
                {"id": 10},
                {"id": 11},
                {"id": 12},
            ]

            update_flags(course_names, 2024)

            assert mock_db.set_advance_enrollment.call_count == 3
            mock_db.set_advance_enrollment.assert_any_call("10")
            mock_db.set_advance_enrollment.assert_any_call("11")
            mock_db.set_advance_enrollment.assert_any_call("12")
