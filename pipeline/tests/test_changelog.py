"""Tests for pipeline/extractors/changelog.py."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from ..extractors.changelog import (
    _parse_gemini_json,
    parse_changelog,
)
from ..models import ChangeEntry


class TestParseGeminiJson:
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
                    "changes": [],
                    "reason": null
                }
            ]
        }"""
        result = _parse_gemini_json(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].change_type == "create"

    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError):
            _parse_gemini_json("not valid json at all")


class TestParseChangelog:
    @patch("pipeline.extractors.changelog._generate_changes_with_model")
    @patch("pipeline.extractors.changelog.Settings")
    def test_successful_parsing(
        self, mock_settings: Mock, mock_generate: Mock
    ) -> None:
        mock_settings.GEMINI_MODEL = "primary-model"
        mock_settings.GEMINI_FALLBACK_MODEL = "fallback-model"
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
        mock_generate.assert_called_once_with("primary-model", b"pdf bytes")

    @patch("pipeline.extractors.changelog.logger")
    @patch("pipeline.extractors.changelog._generate_changes_with_model")
    @patch("pipeline.extractors.changelog.Settings")
    def test_fallback_on_primary_failure(
        self,
        mock_settings: Mock,
        mock_generate: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_settings.GEMINI_MODEL = "primary-model"
        mock_settings.GEMINI_FALLBACK_MODEL = "fallback-model"
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
        mock_logger.warning.assert_called_once()
