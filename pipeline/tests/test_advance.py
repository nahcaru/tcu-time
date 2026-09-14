"""Tests for pipeline/extractors/advance.py."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from ..extractors.advance import (
    _request_course_names,
    clean_text,
    extract_course_names,
    extract_course_names_from_pdf_tables,
)


class TestPdfplumberTableExtraction:
    def test_clean_text(self) -> None:
        assert clean_text("  高度情報システム  \n  特論  ") == "高度情報システム 特論"
        assert clean_text(None) == ""

    @patch("pipeline.extractors.advance.pdfplumber.open")
    def test_extract_course_names_from_tables(self, mock_pdf_open: Mock) -> None:
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.extract_tables.return_value = [
            [
                ["専攻", "科目区分", "授業科目名", "開講期", "単位数"],
                ["情報工学", "専門科目", "高度情報ネットワーク特論", "前期", "2"],
                ["情報工学", "専門科目", "情報セキュリティ特論\n機械学習特論", "後期", "2"],
                ["情報工学", "専門科目", "※履修制限あり", "後期", "2"],
                ["情報工学", "専門科目", "-", "前期", "1"],
                ["情報工学", "専門科目", "高度情報ネットワーク特論", "前期", "2"],  # duplicate
            ]
        ]
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        names = extract_course_names_from_pdf_tables(b"fake pdf")
        assert names == ["高度情報ネットワーク特論", "情報セキュリティ特論", "機械学習特論"]

    @patch("pipeline.extractors.advance.pdfplumber.open")
    def test_extract_returns_empty_when_no_table(self, mock_pdf_open: Mock) -> None:
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        assert extract_course_names_from_pdf_tables(b"fake pdf") == []


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
    @patch("pipeline.extractors.advance.extract_course_names_from_pdf_tables")
    @patch("pipeline.extractors.advance._request_course_names")
    def test_prefers_pdfplumber_when_tables_found(
        self, mock_request: Mock, mock_pdfplumber: Mock
    ) -> None:
        mock_pdfplumber.return_value = ["科目X", "科目Y"]

        result = extract_course_names(b"pdf bytes")
        assert result == ["科目X", "科目Y"]
        mock_request.assert_not_called()

    @patch("pipeline.extractors.advance.extract_course_names_from_pdf_tables")
    @patch("pipeline.extractors.advance._request_course_names")
    @patch("pipeline.extractors.advance.Settings")
    def test_extract_with_primary_model(
        self, mock_settings: Mock, mock_request: Mock, mock_pdfplumber: Mock
    ) -> None:
        mock_pdfplumber.return_value = []
        mock_settings.GEMINI_MODEL = "primary-model"
        mock_settings.GEMINI_FALLBACK_MODEL = "fallback-model"
        mock_request.return_value = ["科目A", "科目B"]

        result = extract_course_names(b"pdf bytes")

        assert result == ["科目A", "科目B"]
        mock_request.assert_called_once_with("primary-model", b"pdf bytes")

    @patch("pipeline.extractors.advance.extract_course_names_from_pdf_tables")
    @patch("pipeline.extractors.advance.logger")
    @patch("pipeline.extractors.advance._request_course_names")
    @patch("pipeline.extractors.advance.Settings")
    def test_extract_fallback_on_primary_failure(
        self,
        mock_settings: Mock,
        mock_request: Mock,
        mock_logger: Mock,
        mock_pdfplumber: Mock,
    ) -> None:
        mock_pdfplumber.side_effect = Exception("Corrupt PDF table")
        mock_settings.GEMINI_MODEL = "primary-model"
        mock_settings.GEMINI_FALLBACK_MODEL = "fallback-model"
        mock_request.side_effect = [Exception("Primary failed"), ["科目C", "科目D"]]

        result = extract_course_names(b"pdf bytes")

        assert result == ["科目C", "科目D"]
        assert mock_request.call_count == 2
        mock_logger.warning.assert_called_once()
