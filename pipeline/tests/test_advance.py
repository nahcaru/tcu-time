"""Tests for pipeline/extractors/advance.py."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from ..extractors.advance import _request_course_names, extract_course_names


class TestRequestCourseNames:
    @patch("pipeline.extractors.advance.create_client")
    @patch("pipeline.extractors.advance.generate_pdf_json")
    def test_valid_response(
        self, mock_generate_pdf_json: Mock, mock_create_client: Mock
    ) -> None:
        mock_create_client.return_value = Mock()
        mock_generate_pdf_json.return_value = json.dumps({"course_names": ["科目A", "科目B"]})

        result = _request_course_names("gemini-model", b"pdf bytes")
        assert result == ["科目A", "科目B"]

    @patch("pipeline.extractors.advance.create_client")
    @patch("pipeline.extractors.advance.generate_pdf_json")
    def test_invalid_shape_raises(
        self, mock_generate_pdf_json: Mock, mock_create_client: Mock
    ) -> None:
        mock_create_client.return_value = Mock()
        mock_generate_pdf_json.return_value = json.dumps(["科目A", "科目B"])

        with pytest.raises(ValueError):
            _request_course_names("gemini-model", b"pdf bytes")


class TestExtractCourseNames:
    @patch("pipeline.extractors.advance._request_course_names")
    @patch("pipeline.extractors.advance.Settings")
    def test_extract_with_primary_model(
        self, mock_settings: Mock, mock_request: Mock
    ) -> None:
        mock_settings.GEMINI_MODEL = "primary-model"
        mock_settings.GEMINI_FALLBACK_MODEL = "fallback-model"
        mock_request.return_value = ["科目A", "科目B"]

        result = extract_course_names(b"pdf bytes")

        assert result == ["科目A", "科目B"]
        mock_request.assert_called_once_with("primary-model", b"pdf bytes")

    @patch("pipeline.extractors.advance.logger")
    @patch("pipeline.extractors.advance._request_course_names")
    @patch("pipeline.extractors.advance.Settings")
    def test_extract_fallback_on_primary_failure(
        self, mock_settings: Mock, mock_request: Mock, mock_logger: Mock
    ) -> None:
        mock_settings.GEMINI_MODEL = "primary-model"
        mock_settings.GEMINI_FALLBACK_MODEL = "fallback-model"
        mock_request.side_effect = [Exception("Primary failed"), ["科目C", "科目D"]]

        result = extract_course_names(b"pdf bytes")

        assert result == ["科目C", "科目D"]
        assert mock_request.call_count == 2
        mock_logger.warning.assert_called_once()
