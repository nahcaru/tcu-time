"""Tests for pipeline/changelog.py (parse-only, no DB reflection)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from ..changelog import (
    _parse_gemini_json,
    parse_changelog,
)
from ..models import ChangeEntry, FieldChange


class TestParseGeminiJson:
    """Tests for _parse_gemini_json function."""

    def test_valid_json_list(self) -> None:
        raw = """{
            "entries": [
                {
                    "change_type": "create",
                    "course_code": "smab020161",
                    "course_name": "ロボティクス特論",
                    "term": "前期",
                    "day": "月",
                    "period": 1,
                    "changes": [
                        {
                            "field": "教室",
                            "old_value": null,
                            "new_value": "22A"
                        }
                    ],
                    "reason": null
                }
            ]
        }"""
        result = _parse_gemini_json(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].change_type == "create"
        assert result[0].course_code == "smab020161"
        assert len(result[0].changes) == 1

    def test_valid_json_dict_with_entries_key(self) -> None:
        raw = """{
            "entries": [
                {
                    "change_type": "update",
                    "course_code": "smab020162",
                    "course_name": "AI特論",
                    "term": "後期",
                    "day": "木",
                    "period": 2,
                    "changes": [],
                    "reason": "Time change"
                }
            ]
        }"""
        result = _parse_gemini_json(raw)
        assert len(result) == 1
        assert result[0].change_type == "update"

    def test_valid_json_dict_with_change_type_key(self) -> None:
        raw = """{
            "change_type": "delete",
            "course_code": "smab020163",
            "course_name": "データ科学",
            "term": "前期後",
            "day": null,
            "period": null,
            "changes": [],
            "reason": "Cancelled"
        }"""
        result = _parse_gemini_json(raw)
        assert len(result) == 1
        assert result[0].change_type == "delete"

    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError):
            _parse_gemini_json("not valid json at all")

    def test_unexpected_dict_structure(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _parse_gemini_json('{"something": "unexpected"}')

    def test_multiple_entries_in_list(self) -> None:
        raw = """{
            "entries": [
                {
                    "change_type": "create",
                    "course_code": "smab020161",
                    "course_name": "Course1",
                    "term": "前期",
                    "day": "月",
                    "period": 1,
                    "changes": [],
                    "reason": null
                },
                {
                    "change_type": "update",
                    "course_code": "smab020162",
                    "course_name": "Course2",
                    "term": "後期",
                    "day": "木",
                    "period": 2,
                    "changes": [],
                    "reason": null
                }
            ]
        }"""
        result = _parse_gemini_json(raw)
        assert len(result) == 2

    def test_field_change_parsing(self) -> None:
        raw = """{
            "entries": [
                {
                    "change_type": "update",
                    "course_code": "smab020161",
                    "course_name": "Test",
                    "term": "前期",
                    "day": "月",
                    "period": 1,
                    "changes": [
                        {
                            "field": "講師",
                            "old_value": "佐藤",
                            "new_value": "田中"
                        }
                    ],
                    "reason": null
                }
            ]
        }"""
        result = _parse_gemini_json(raw)
        change = result[0].changes[0]
        assert change.field == "講師"
        assert change.old_value == "佐藤"
        assert change.new_value == "田中"

    def test_string_period_parsed(self) -> None:
        raw = """{
            "entries": [{
                "change_type": "delete",
                "course_code": null,
                "course_name": "集中講義A",
                "term": "前集中",
                "day": null,
                "period": "集中",
                "changes": [],
                "reason": "担当者都合"
            }]
        }"""
        result = _parse_gemini_json(raw)
        assert result[0].period == "集中"

    def test_numeric_string_period_coerced_to_int(self) -> None:
        raw = """{
            "entries": [{
                "change_type": "update",
                "course_code": "smab020161",
                "course_name": "Test",
                "term": "前期",
                "day": "月",
                "period": "3",
                "changes": [],
                "reason": null
            }]
        }"""
        result = _parse_gemini_json(raw)
        assert result[0].period == 3
        assert isinstance(result[0].period, int)





class TestParseChangelog:
    """Tests for parse_changelog function — now parse-only (no DB reflection)."""

    @patch("pipeline.changelog._generate_changes_with_model")
    @patch("pipeline.changelog._extract_all_text")
    @patch("pipeline.changelog.genai.Client")
    def test_successful_parsing(
        self, mock_client_class: Mock, mock_extract: Mock, mock_generate: Mock
    ) -> None:
        mock_extract.return_value = "Extracted text"
        change_entries = [
            ChangeEntry(
                change_type="create",
                course_code="smab020161",
                course_name="Test",
                term="前期",
                day="月",
                period=1,
                changes=[],
            )
        ]
        mock_generate.return_value = change_entries

        result = parse_changelog(b"pdf bytes")

        assert result == change_entries
        mock_extract.assert_called_once_with(b"pdf bytes")
        # No DB calls should have been made
        mock_generate.assert_called_once()

    @patch("pipeline.changelog._generate_changes_with_model")
    @patch("pipeline.changelog._extract_all_text")
    @patch("pipeline.changelog.genai.Client")
    @patch("pipeline.changelog.logger")
    def test_fallback_on_primary_failure(
        self,
        mock_logger: Mock,
        mock_client_class: Mock,
        mock_extract: Mock,
        mock_generate: Mock,
    ) -> None:
        mock_extract.return_value = "Extracted text"
        change_entries = [
            ChangeEntry(
                change_type="update",
                course_code="smab020162",
                course_name="Fallback",
                term="後期",
                day="木",
                period=2,
                changes=[],
            )
        ]
        mock_generate.side_effect = [Exception("Primary failed"), change_entries]

        result = parse_changelog(b"pdf bytes")

        assert result == change_entries
        assert mock_generate.call_count == 2
        mock_logger.warning.assert_called()

    @patch("pipeline.changelog._generate_changes_with_model")
    @patch("pipeline.changelog._extract_all_text")
    @patch("pipeline.changelog.genai.Client")
    def test_returns_list_of_change_entries(
        self, mock_client_class: Mock, mock_extract: Mock, mock_generate: Mock
    ) -> None:
        """parse_changelog returns list[ChangeEntry] — no side effects."""
        mock_extract.return_value = "Some text"
        mock_generate.return_value = []

        result = parse_changelog(b"pdf bytes")

        assert result == []
        assert isinstance(result, list)
