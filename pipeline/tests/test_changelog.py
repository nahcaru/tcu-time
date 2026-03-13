from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from ..changelog import (
    _entry_to_course_upsert_payload,
    _extract_all_text,
    _find_course_for_change,
    _parse_gemini_json,
    apply_changelog,
    parse_changelog,
)
from ..models import ChangeEntry, ChangeType, FieldChange


class TestParseGeminiJson:
    """Tests for _parse_gemini_json function."""

    def test_valid_json_list(self) -> None:
        """Valid JSON list of change entries returns list[ChangeEntry]."""
        raw = """[
            {
                "change_type": "add",
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
        ]"""
        result = _parse_gemini_json(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].change_type == "add"
        assert result[0].course_code == "smab020161"
        assert len(result[0].changes) == 1

    def test_valid_json_dict_with_entries_key(self) -> None:
        """Valid JSON dict with 'entries' key unwraps and returns list[ChangeEntry]."""
        raw = """{
            "entries": [
                {
                    "change_type": "modify",
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
        assert result[0].change_type == "modify"
        assert result[0].course_code == "smab020162"

    def test_valid_json_dict_with_change_type_key(self) -> None:
        """Valid JSON dict with 'change_type' key wraps in list."""
        raw = """{
            "change_type": "cancel",
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
        assert result[0].change_type == "cancel"

    def test_invalid_json(self) -> None:
        """Invalid JSON raises ValueError."""
        raw = "not valid json at all"
        with pytest.raises(ValueError):
            _parse_gemini_json(raw)

    def test_non_list_non_dict(self) -> None:
        """Non-list/dict response raises ValueError."""
        raw = '"just a string"'
        with pytest.raises(ValueError, match="Gemini response is not JSON object/array"):
            _parse_gemini_json(raw)

    def test_unexpected_dict_structure(self) -> None:
        """Unexpected dict structure raises ValueError."""
        raw = '{"something": "unexpected"}'
        with pytest.raises(ValueError, match="Unexpected JSON structure from Gemini"):
            _parse_gemini_json(raw)

    def test_multiple_entries_in_list(self) -> None:
        """Multiple entries in list are all parsed."""
        raw = """[
            {
                "change_type": "add",
                "course_code": "smab020161",
                "course_name": "Course1",
                "term": "前期",
                "day": "月",
                "period": 1,
                "changes": [],
                "reason": null
            },
            {
                "change_type": "modify",
                "course_code": "smab020162",
                "course_name": "Course2",
                "term": "後期",
                "day": "木",
                "period": 2,
                "changes": [],
                "reason": null
            }
        ]"""
        result = _parse_gemini_json(raw)
        assert len(result) == 2
        assert result[0].course_code == "smab020161"
        assert result[1].course_code == "smab020162"

    def test_field_change_parsing(self) -> None:
        """FieldChange objects are correctly parsed."""
        raw = """[
            {
                "change_type": "modify",
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
        ]"""
        result = _parse_gemini_json(raw)
        assert len(result[0].changes) == 1
        change = result[0].changes[0]
        assert change.field == "講師"
        assert change.old_value == "佐藤"
        assert change.new_value == "田中"

    def test_string_period_parsed(self) -> None:
        raw = """[{
            "change_type": "cancel",
            "course_code": null,
            "course_name": "集中講義A",
            "term": "前集中",
            "day": null,
            "period": "集中",
            "changes": [],
            "reason": "担当者都合"
        }]"""
        result = _parse_gemini_json(raw)
        assert len(result) == 1
        assert result[0].period == "集中"

    def test_numeric_string_period_coerced_to_int(self) -> None:
        raw = """[{
            "change_type": "modify",
            "course_code": "smab020161",
            "course_name": "Test",
            "term": "前期",
            "day": "月",
            "period": "3",
            "changes": [],
            "reason": null
        }]"""
        result = _parse_gemini_json(raw)
        assert result[0].period == 3
        assert isinstance(result[0].period, int)


class TestExtractAllText:
    """Tests for _extract_all_text function."""

    def test_single_page_pdf(self) -> None:
        """Single page PDF text extraction."""
        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Page 1 text"
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf

            pdf_bytes = b"fake pdf content"
            result = _extract_all_text(pdf_bytes)

            assert result == "Page 1 text"
            mock_open.assert_called_once()

    def test_multiple_pages_pdf(self) -> None:
        """Multiple page PDF text extraction joins with double newline."""
        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            page1 = MagicMock()
            page1.extract_text.return_value = "Page 1"
            page2 = MagicMock()
            page2.extract_text.return_value = "Page 2"
            mock_pdf.pages = [page1, page2]
            mock_open.return_value.__enter__.return_value = mock_pdf

            result = _extract_all_text(b"")
            assert result == "Page 1\n\nPage 2"

    def test_empty_page_handling(self) -> None:
        """Empty pages (None text) are handled gracefully."""
        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            page1 = MagicMock()
            page1.extract_text.return_value = "Text"
            page2 = MagicMock()
            page2.extract_text.return_value = None
            mock_pdf.pages = [page1, page2]
            mock_open.return_value.__enter__.return_value = mock_pdf

            result = _extract_all_text(b"")
            assert result == "Text"


class TestEntryToCourseUpsertPayload:
    """Tests for _entry_to_course_upsert_payload function."""

    def test_basic_entry(self) -> None:
        """Basic entry with code, name, term, day, period."""
        entry = ChangeEntry(
            change_type="add",
            course_code="smab020161",
            course_name="ロボティクス特論",
            term="前期",
            day="月",
            period=1,
            changes=[],
            reason=None,
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert result["code"] == "smab020161"
        assert result["name"] == "ロボティクス特論"
        assert result["semester"] == "spring"
        assert result["instructors"] == ["未定"]
        assert result["source_type"] == "changelog"
        assert "code" in result
        assert "name" in result
        assert "instructors" in result
        assert "year_level" in result
        assert "class_section" in result
        assert "semester" in result
        assert "schedules" in result
        assert "target_raw" in result
        assert "targets" in result
        assert "notes" in result
        assert "source_type" in result

    def test_entry_with_instructor_change(self) -> None:
        """Entry with instructor change parses instructors from change."""
        entry = ChangeEntry(
            change_type="modify",
            course_code="smab020161",
            course_name="Test",
            term="前期",
            day="月",
            period=1,
            changes=[
                FieldChange(field="担当者", old_value="佐藤", new_value="田中\n佐野")
            ],
            reason=None,
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert result["instructors"] == ["田中", "佐野"]

    def test_entry_with_room_change(self) -> None:
        """Entry with room change includes room in schedule."""
        entry = ChangeEntry(
            change_type="modify",
            course_code="smab020161",
            course_name="Test",
            term="前期",
            day="月",
            period=1,
            changes=[FieldChange(field="教室", old_value=None, new_value="22A")],
            reason=None,
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert len(result["schedules"]) == 1
        assert result["schedules"][0]["room"] == "22A"

    def test_entry_without_code(self) -> None:
        """Entry without code has code=None in output."""
        entry = ChangeEntry(
            change_type="add",
            course_code=None,
            course_name="Nameless",
            term="前期",
            day="月",
            period=1,
            changes=[],
            reason=None,
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert result["code"] is None

    def test_entry_with_reason(self) -> None:
        """Entry with reason populates notes field."""
        entry = ChangeEntry(
            change_type="cancel",
            course_code="smab020161",
            course_name="Test",
            term="前期",
            day="月",
            period=1,
            changes=[],
            reason="Instructor unavailable",
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert result["notes"] == "Instructor unavailable"

    def test_entry_with_name_change(self) -> None:
        """Entry with course name change updates name field."""
        entry = ChangeEntry(
            change_type="modify",
            course_code="smab020161",
            course_name="Old Name",
            term="前期",
            day="月",
            period=1,
            changes=[FieldChange(field="科目名", old_value="Old Name", new_value="New Name")],
            reason=None,
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert result["name"] == "New Name"

    def test_entry_without_schedule_info(self) -> None:
        """Entry without term/day/period has empty schedules."""
        entry = ChangeEntry(
            change_type="add",
            course_code="smab020161",
            course_name="Test",
            term=None,
            day=None,
            period=None,
            changes=[],
            reason=None,
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert result["schedules"] == []

    def test_entry_with_string_period_has_empty_schedule(self) -> None:
        entry = ChangeEntry(
            change_type="add",
            course_code="smab020161",
            course_name="集中講義A",
            term="前集中",
            day="月",
            period="集中",
            changes=[],
            reason=None,
        )
        result = _entry_to_course_upsert_payload(entry, semester="spring")

        assert result["schedules"] == []


class TestFindCourseForChange:
    """Tests for _find_course_for_change function."""

    @patch("pipeline.changelog.db.find_course")
    def test_priority_1_code_match(self, mock_find: Mock) -> None:
        """Priority 1: code matches."""
        mock_course = {"id": "123", "code": "smab020161"}
        mock_find.return_value = mock_course

        entry = ChangeEntry(
            change_type="modify",
            course_code="smab020161",
            course_name="Test",
            term="前期",
            day="月",
            period=1,
            changes=[],
        )
        result = _find_course_for_change(entry)

        assert result == mock_course
        mock_find.assert_called_with(code="smab020161")

    @patch("pipeline.changelog.db.find_course")
    def test_priority_2_name_term_day_period_match(self, mock_find: Mock) -> None:
        """Priority 2: name+term+day+period match when code miss."""
        mock_course = {"id": "456", "name": "Test Course"}
        mock_find.side_effect = [None, mock_course]  # First call: code miss, second: name+term match

        entry = ChangeEntry(
            change_type="modify",
            course_code="smab999999",
            course_name="Test Course",
            term="前期",
            day="月",
            period=1,
            changes=[],
        )
        result = _find_course_for_change(entry)

        assert result == mock_course
        assert mock_find.call_count == 2

    @patch("pipeline.changelog.db.find_course")
    @patch("pipeline.changelog.db.get_client")
    def test_string_period_skips_priority_2(
        self, mock_get_client: Mock, mock_find: Mock
    ) -> None:
        mock_find.return_value = None
        mock_table = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "789", "name": "集中講義A", "schedules": [{"term": "前集中"}]}
        ]
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client

        entry = ChangeEntry(
            change_type="cancel",
            course_code=None,
            course_name="集中講義A",
            term="前集中",
            day=None,
            period="集中",
            changes=[],
        )
        result = _find_course_for_change(entry)

        assert result is not None
        assert result["id"] == "789"
        mock_find.assert_not_called()

    @patch("pipeline.changelog.db.find_course")
    @patch("pipeline.changelog.db.get_client")
    def test_priority_3_name_and_term_query(
        self, mock_get_client: Mock, mock_find: Mock
    ) -> None:
        """Priority 3: database query when priorities 1 & 2 miss."""
        mock_find.return_value = None
        mock_table = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "789", "name": "Test", "schedules": [{"term": "前期"}]}
        ]
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client

        entry = ChangeEntry(
            change_type="modify",
            course_code=None,
            course_name="Test",
            term="前期",
            day=None,
            period=None,
            changes=[],
        )
        result = _find_course_for_change(entry)

        assert result == mock_result.data[0]
        mock_table.select.assert_called()
        mock_table.select.return_value.eq.assert_called()

    @patch("pipeline.changelog.db.find_course")
    @patch("pipeline.changelog.db.get_client")
    def test_all_priorities_miss_returns_none(
        self, mock_get_client: Mock, mock_find: Mock
    ) -> None:
        """All priorities miss returns None."""
        mock_find.return_value = None
        mock_table = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client

        entry = ChangeEntry(
            change_type="modify",
            course_code=None,
            course_name="Nonexistent",
            term="前期",
            day=None,
            period=None,
            changes=[],
        )
        result = _find_course_for_change(entry)

        assert result is None

    @patch("pipeline.changelog.db.find_course")
    @patch("pipeline.changelog.db.get_client")
    def test_multiple_candidates_logs_warning(
        self, mock_get_client: Mock, mock_find: Mock
    ) -> None:
        """Multiple candidates at priority 3 logs warning and returns first."""
        mock_find.return_value = None
        mock_table = MagicMock()
        candidates = [
            {"id": "1", "name": "Test", "schedules": [{"term": "前期"}]},
            {"id": "2", "name": "Test", "schedules": [{"term": "前期"}]},
        ]
        mock_result = MagicMock()
        mock_result.data = candidates
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_client = MagicMock()
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client

        entry = ChangeEntry(
            change_type="modify",
            course_code=None,
            course_name="Test",
            term="前期",
            day=None,
            period=None,
            changes=[],
        )

        with patch("pipeline.changelog.logger") as mock_logger:
            result = _find_course_for_change(entry)
            assert result == candidates[0]
            mock_logger.warning.assert_called()


class TestParseChangelog:
    """Tests for parse_changelog function."""

    @patch("pipeline.changelog._generate_changes_with_model")
    @patch("pipeline.changelog._extract_all_text")
    @patch("pipeline.changelog.genai.Client")
    def test_successful_parsing(
        self, mock_client_class: Mock, mock_extract: Mock, mock_generate: Mock
    ) -> None:
        """Successful changelog parsing returns list[ChangeEntry]."""
        mock_extract.return_value = "Extracted text"
        change_entries = [
            ChangeEntry(
                change_type="add",
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
        """Primary Gemini fails, fallback succeeds."""
        mock_extract.return_value = "Extracted text"
        change_entries = [
            ChangeEntry(
                change_type="modify",
                course_code="smab020162",
                course_name="Fallback",
                term="後期",
                day="木",
                period=2,
                changes=[],
            )
        ]

        # First call raises, second succeeds
        mock_generate.side_effect = [Exception("Primary failed"), change_entries]

        result = parse_changelog(b"pdf bytes")

        assert result == change_entries
        assert mock_generate.call_count == 2
        mock_logger.warning.assert_called()


class TestApplyChangelog:
    """Tests for apply_changelog function."""

    @patch("pipeline.changelog.logger")
    @patch("pipeline.changelog.db.upsert_courses")
    @patch("pipeline.changelog._entry_to_course_upsert_payload")
    def test_apply_add_change(
        self,
        mock_payload: Mock,
        mock_upsert: Mock,
        mock_logger: Mock,
    ) -> None:
        """Add change calls upsert_courses with source_type='changelog'."""
        mock_payload.return_value = {
            "code": "smab020161",
            "name": "New Course",
            "source_type": "changelog",
        }

        entry = ChangeEntry(
            change_type="add",
            course_code="smab020161",
            course_name="New Course",
            term="前期",
            day="月",
            period=1,
            changes=[],
        )

        apply_changelog([entry], semester="spring")

        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args
        assert call_args[0][0][0]["source_type"] == "changelog"
        assert call_args[1]["source_type"] == "changelog"

    @patch("pipeline.changelog.logger")
    @patch("pipeline.changelog.db.update_course_fields")
    @patch("pipeline.changelog._find_course_for_change")
    def test_apply_modify_change(
        self, mock_find: Mock, mock_update: Mock, mock_logger: Mock
    ) -> None:
        """Modify change calls update_course_fields."""
        mock_find.return_value = {"id": "course_123"}
        change = FieldChange(field="講師", old_value="Old", new_value="New")

        entry = ChangeEntry(
            change_type="modify",
            course_code="smab020161",
            course_name="Test",
            term="前期",
            day="月",
            period=1,
            changes=[change],
        )

        apply_changelog([entry], semester="spring")

        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == "course_123"

    @patch("pipeline.changelog.logger")
    @patch("pipeline.changelog.db.mark_cancelled")
    @patch("pipeline.changelog._find_course_for_change")
    def test_apply_cancel_change(
        self, mock_find: Mock, mock_cancel: Mock, mock_logger: Mock
    ) -> None:
        """Cancel change calls mark_cancelled."""
        mock_find.return_value = {"id": "course_456"}

        entry = ChangeEntry(
            change_type="cancel",
            course_code="smab020161",
            course_name="Test",
            term="前期",
            day="月",
            period=1,
            changes=[],
            reason="Cancelled for safety",
        )

        apply_changelog([entry], semester="spring")

        mock_cancel.assert_called_once()
        call_args = mock_cancel.call_args
        assert call_args[0][0] == "course_456"
        assert call_args[1]["reason"] == "Cancelled for safety"

    @patch("pipeline.changelog.logger")
    @patch("pipeline.changelog.db.upsert_courses")
    @patch("pipeline.changelog._entry_to_course_upsert_payload")
    def test_add_without_code_skipped(
        self,
        mock_payload: Mock,
        mock_upsert: Mock,
        mock_logger: Mock,
    ) -> None:
        """Add change without code is skipped, upsert_courses NOT called."""
        mock_payload.return_value = {"code": None, "name": "No Code"}

        entry = ChangeEntry(
            change_type="add",
            course_code=None,
            course_name="No Code",
            term="前期",
            day="月",
            period=1,
            changes=[],
        )

        apply_changelog([entry], semester="spring")

        mock_upsert.assert_not_called()
        mock_logger.warning.assert_called()

    @patch("pipeline.changelog.logger")
    @patch("pipeline.changelog.db.update_course_fields")
    @patch("pipeline.changelog._find_course_for_change")
    def test_modify_without_matching_course_logs_warning(
        self, mock_find: Mock, mock_update: Mock, mock_logger: Mock
    ) -> None:
        """Modify with no matching course logs warning, no crash."""
        mock_find.return_value = None

        entry = ChangeEntry(
            change_type="modify",
            course_code=None,
            course_name="Nonexistent",
            term="前期",
            day="月",
            period=1,
            changes=[],
        )

        # Should not raise
        apply_changelog([entry], semester="spring")

        mock_update.assert_not_called()
        mock_logger.warning.assert_called()

    @patch("pipeline.changelog.logger")
    @patch("pipeline.changelog.db.upsert_courses")
    @patch("pipeline.changelog.db.update_course_fields")
    @patch("pipeline.changelog.db.mark_cancelled")
    @patch("pipeline.changelog._entry_to_course_upsert_payload")
    @patch("pipeline.changelog._find_course_for_change")
    def test_mixed_changes_all_applied(
        self,
        mock_find: Mock,
        mock_payload: Mock,
        mock_cancel: Mock,
        mock_update: Mock,
        mock_upsert: Mock,
        mock_logger: Mock,
    ) -> None:
        """Mixed add, modify, and cancel changes are all applied."""
        mock_payload.return_value = {
            "code": "smab020161",
            "name": "New",
            "source_type": "changelog",
        }
        mock_find.side_effect = [
            {"id": "course_2"},  # For modify
            {"id": "course_3"},  # For cancel
        ]

        changes = [
            ChangeEntry(
                change_type="add",
                course_code="smab020161",
                course_name="New",
                term="前期",
                day="月",
                period=1,
                changes=[],
            ),
            ChangeEntry(
                change_type="modify",
                course_code="smab020162",
                course_name="Existing",
                term="前期",
                day="木",
                period=2,
                changes=[],
            ),
            ChangeEntry(
                change_type="cancel",
                course_code="smab020163",
                course_name="ToCancel",
                term="後期",
                day="火",
                period=3,
                changes=[],
            ),
        ]

        apply_changelog(changes, semester="spring")

        mock_upsert.assert_called_once()
        mock_update.assert_called_once()
        mock_cancel.assert_called_once()

        # Check final log message
        final_log_call = mock_logger.info.call_args
        assert final_log_call[0][1:] == (1, 1, 1)

    @patch("pipeline.changelog.logger")
    @patch("pipeline.changelog.db.upsert_courses")
    @patch("pipeline.changelog._entry_to_course_upsert_payload")
    def test_apply_with_academic_year(
        self,
        mock_payload: Mock,
        mock_upsert: Mock,
        mock_logger: Mock,
    ) -> None:
        """Academic year is passed to upsert_courses."""
        mock_payload.return_value = {
            "code": "smab020161",
            "name": "Test",
            "source_type": "changelog",
        }

        entry = ChangeEntry(
            change_type="add",
            course_code="smab020161",
            course_name="Test",
            term="前期",
            day="月",
            period=1,
            changes=[],
        )

        apply_changelog([entry], semester="spring", academic_year=2024)

        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args
        assert call_args[1]["academic_year"] == 2024
