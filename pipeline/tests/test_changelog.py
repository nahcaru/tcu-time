"""Tests for pipeline/extractors/changelog.py."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from ..extractors.changelog import (
    _detect_headers,
    _parse_gemini_json,
    _parse_table_row,
    clean_text,
    extract_changelog_from_pdf_tables,
    parse_changelog,
    parse_day_period,
)
from ..models import ChangeEntry, FieldChange


class TestTextAndScheduleHelpers:
    def test_clean_text(self) -> None:
        assert clean_text("  hello world  ") == "hello world"
        assert clean_text("12N\n") == "12N"
        assert (
            clean_text("Sustainable Cyber-\nPhysical Systems")
            == "Sustainable Cyber-Physical Systems"
        )
        assert clean_text("33G（横浜キャ\nンパス）") == "33G(横浜キャンパス)"
        assert clean_text("パワーエレクトロニクス特\n論") == "パワーエレクトロニクス特論"
        assert clean_text(None) == ""

    def test_parse_day_period(self) -> None:
        assert parse_day_period("火1,金1") == ("火", 1)
        assert parse_day_period("木３") == ("木", 3)
        assert parse_day_period("月5,木5") == ("月", 5)
        assert parse_day_period("金2") == ("金", 2)
        assert parse_day_period("前集中") == (None, "集中")
        assert parse_day_period("") == (None, None)
        assert parse_day_period("-") == (None, None)
        assert parse_day_period(None) == (None, None)


class TestHeaderDetection:
    def test_detect_valid_headers(self) -> None:
        raw_headers = [
            "変更",
            "開講",
            "クラス",
            "曜日時限",
            "学期",
            "学年",
            "科目名",
            "講義コード",
            "教室",
            "受講対象",
            "再履修者科目名",
            "備考",
            "担当者",
        ]
        detected = _detect_headers(raw_headers)
        assert detected is not None
        assert "科目名" in detected
        assert "講義コード" in detected
        assert "教室" in detected
        assert "再履修者科目名" in detected
        # Ensure 再履修者科目名 was not overwritten as 科目名
        assert detected[6] == "科目名"
        assert detected[10] == "再履修者科目名"

    def test_detect_invalid_headers(self) -> None:
        assert _detect_headers([]) is None
        assert _detect_headers(["タイトル", "日付", "備考"]) is None


class TestParseTableRow:
    def setup_method(self) -> None:
        self.headers = [
            "変更",
            "開講",
            "クラス",
            "曜日時限",
            "学期",
            "学年",
            "科目名",
            "講義コード",
            "教室",
            "受講対象",
            "再履修者科目名",
            "備考",
            "担当者",
        ]

    def test_parse_update_row_classroom(self) -> None:
        row = [
            "2025/4/9 17:14",
            "院総",
            "",
            "火1,金1",
            "前期前",
            "1",
            "機械学習特論",
            "smaa100181",
            "12N\n→共用演習室",
            "10情報",
            "",
            "",
            "神野 健哉,ニーナ スヴィリドヴァ",
        ]
        entry = _parse_table_row(row, self.headers)
        assert entry is not None
        assert entry.change_type == "update"
        assert entry.course_code == "smaa100181"
        assert entry.course_name == "機械学習特論"
        assert entry.term == "前期前"
        assert entry.day == "火"
        assert entry.period == 1
        assert len(entry.changes) == 1
        assert entry.changes[0].field == "教室"
        assert entry.changes[0].old_value == "12N"
        assert entry.changes[0].new_value == "共用演習室"

    def test_parse_update_row_empty_old_classroom(self) -> None:
        row = [
            "2025/4/11 16:42",
            "院総",
            "",
            "金2",
            "前期",
            "1",
            "情報理論特論",
            "smaz090041",
            "→12H",
            "09情報",
            "",
            "",
            "新家 稔央",
        ]
        entry = _parse_table_row(row, self.headers)
        assert entry is not None
        assert entry.change_type == "update"
        assert entry.course_code == "smaz090041"
        assert len(entry.changes) == 1
        assert entry.changes[0].field == "教室"
        assert entry.changes[0].old_value is None
        assert entry.changes[0].new_value == "12H"

    def test_parse_update_row_instructors(self) -> None:
        row = [
            "2025/4/23 17:22",
            "院総",
            "",
            "",
            "後集中",
            "1",
            "画像解析特論",
            "smbz100141",
            "",
            "10情報",
            "",
            "",
            "向井 信彦\n→盧 承鐸",
        ]
        entry = _parse_table_row(row, self.headers)
        assert entry is not None
        assert entry.change_type == "update"
        assert entry.course_code == "smbz100141"
        assert len(entry.changes) == 1
        assert entry.changes[0].field == "担当者"
        assert entry.changes[0].old_value == "向井 信彦"
        assert entry.changes[0].new_value == "盧 承鐸"

    def test_parse_update_row_schedule(self) -> None:
        row = [
            "2025/4/23 17:22",
            "院総",
            "",
            "火2\n→火2,金2",
            "後期後",
            "1",
            "溶液科学特論",
            "smbb110021",
            "",
            "11自然",
            "～19誘電体特論",
            "",
            "須藤 誠一",
        ]
        entry = _parse_table_row(row, self.headers)
        assert entry is not None
        assert entry.change_type == "update"
        assert entry.course_code == "smbb110021"
        # Identification fields use old value before arrow
        assert entry.day == "火"
        assert entry.period == 2
        assert len(entry.changes) == 1
        assert entry.changes[0].field == "曜日時限"
        assert entry.changes[0].old_value == "火2"
        assert entry.changes[0].new_value == "火2,金2"

    def test_parse_deletion_row(self) -> None:
        row = [
            "2025/4/9 17:14",
            "院総\n→（削除）",
            "→（削除）",
            "月5,木5\n→（削除）",
            "前期後\n→（削除）",
            "1\n→（削除）",
            "プラズマ応用工学特論\n→（削除）",
            "smab030111\n→（削除）",
            "12M\n→（削除）",
            "03電気・化学\n→（削除）",
            "→（削除）",
            "→（削除）",
            "未定\n→（削除）",
        ]
        entry = _parse_table_row(row, self.headers)
        assert entry is not None
        assert entry.change_type == "delete"
        assert entry.course_code == "smab030111"
        assert entry.course_name == "プラズマ応用工学特論"
        assert entry.term == "前期後"
        assert entry.day == "月"
        assert entry.period == 5
        assert entry.changes == []

    def test_parse_creation_row(self) -> None:
        row = [
            "2025/4/30 15:53",
            "（新規）\n→院総",
            "（新規）\n→",
            "（新規）\n→水1,水2",
            "（新規）\n→前期前",
            "（新規）\n→1",
            "（新規）\n→IoT for SDGs",
            "（新規）\n→ymaa3101",
            "（新規）\n→33G（横浜キャ\nンパス）",
            "（新規）\n→00共通",
            "（新規）\n→",
            "（新規）\n→",
            "（新規）\n→長沢 敬祐",
        ]
        entry = _parse_table_row(row, self.headers)
        assert entry is not None
        assert entry.change_type == "create"
        assert entry.course_code == "ymaa3101"
        assert entry.course_name == "IoT for SDGs"
        assert entry.term == "前期前"
        assert entry.day == "水"
        assert entry.period == 1
        assert entry.changes == []


class TestExtractFromPDFTables:
    @patch("pipeline.extractors.changelog.pdfplumber.open")
    def test_extract_tables_with_mock(self, mock_pdfplumber_open: Mock) -> None:
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.extract_tables.return_value = [
            [
                [
                    "変更",
                    "開講",
                    "クラス",
                    "曜日時限",
                    "学期",
                    "学年",
                    "科目名",
                    "講義コード",
                    "教室",
                    "受講対象",
                    "再履修者科目名",
                    "備考",
                    "担当者",
                ],
                [
                    "2025/4/9 17:14",
                    "院総",
                    "",
                    "火1,金1",
                    "前期前",
                    "1",
                    "機械学習特論",
                    "smaa100181",
                    "12N\n→共用演習室",
                    "10情報",
                    "",
                    "",
                    "神野 健哉,ニーナ スヴィリドヴァ",
                ],
                # Duplicate row to test deduplication
                [
                    "2025/4/9 17:14",
                    "院総",
                    "",
                    "火1,金1",
                    "前期前",
                    "1",
                    "機械学習特論",
                    "smaa100181",
                    "12N\n→共用演習室",
                    "10情報",
                    "",
                    "",
                    "神野 健哉,ニーナ スヴィリドヴァ",
                ],
                [
                    "2025/4/30 15:53",
                    "（新規）\n→院総",
                    "（新規）\n→",
                    "（新規）\n→水1,水2",
                    "（新規）\n→前期前",
                    "（新規）\n→1",
                    "（新規）\n→IoT for SDGs",
                    "（新規）\n→ymaa3101",
                    "（新規）\n→33G（横浜キャ\nンパス）",
                    "（新規）\n→00共通",
                    "（新規）\n→",
                    "（新規）\n→",
                    "（新規）\n→長沢 敬祐",
                ],
            ]
        ]
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdfplumber_open.return_value = mock_pdf

        entries = extract_changelog_from_pdf_tables(b"fake pdf")
        # Should deduplicate the 2 identical rows into 1
        assert len(entries) == 2
        assert entries[0].change_type == "update"
        assert entries[0].course_code == "smaa100181"
        assert entries[1].change_type == "create"
        assert entries[1].course_code == "ymaa3101"


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

    def test_normalizes_legacy_change_types(self) -> None:
        raw = """{
            "entries": [
                {
                    "change_type": "modify",
                    "course_code": "smab020161",
                    "course_name": "ロボティクス特論",
                    "term": "前期",
                    "day": "月",
                    "period": 1,
                    "changes": []
                },
                {
                    "change_type": "cancel",
                    "course_code": "smab020162",
                    "course_name": "AI特論",
                    "term": "前期",
                    "day": "火",
                    "period": 2,
                    "changes": []
                },
                {
                    "change_type": "add",
                    "course_code": "smab020163",
                    "course_name": "データサイエンス特論",
                    "term": "前期",
                    "day": "水",
                    "period": 3,
                    "changes": []
                }
            ]
        }"""
        result = _parse_gemini_json(raw)
        assert len(result) == 3
        assert result[0].change_type == "update"
        assert result[1].change_type == "delete"
        assert result[2].change_type == "create"


class TestParseChangelog:
    @patch("pipeline.extractors.changelog.extract_changelog_from_pdf_tables")
    def test_table_extraction_success_skips_gemini(
        self, mock_extract_tables: Mock
    ) -> None:
        change_entries = [
            ChangeEntry(
                change_type="update",
                course_code="smab020161",
                course_name="Table Course",
                term="前期",
                day="月",
                period=1,
                changes=[],
            )
        ]
        mock_extract_tables.return_value = change_entries

        result = parse_changelog(b"some pdf bytes")
        assert result == change_entries
        mock_extract_tables.assert_called_once_with(b"some pdf bytes")

    @patch("pipeline.extractors.changelog.extract_changelog_from_pdf_tables")
    @patch("pipeline.extractors.changelog._generate_changes_with_model")
    @patch("pipeline.extractors.changelog.Settings")
    def test_fallback_to_gemini_when_no_tables_found(
        self,
        mock_settings: Mock,
        mock_generate: Mock,
        mock_extract_tables: Mock,
    ) -> None:
        mock_extract_tables.return_value = []
        mock_settings.GEMINI_MODEL = "primary-model"
        mock_settings.GEMINI_FALLBACK_MODEL = "fallback-model"
        change_entries = [
            ChangeEntry(
                change_type="create",
                course_code="smab020161",
                course_name="Fallback Gemini",
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

