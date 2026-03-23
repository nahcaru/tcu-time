"""Tests for pipeline/main.py (approval-flow orchestrator)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest

from ..main import (
    _detect_academic_year,
    _handle_advance_enrollment,
    _handle_changelog,
    _handle_timetable,
    run_pipeline,
)
from ..models import PDFType, Semester


# =============================================================================
# Test _detect_academic_year()
# =============================================================================


class TestDetectAcademicYear:
    def test_detects_year_from_url_with_uploads_2025(self) -> None:
        url = "https://example.com/uploads/2025/04/abc123.pdf"
        assert _detect_academic_year(url) == 2025

    def test_detects_year_from_url_with_uploads_2024(self) -> None:
        url = "https://example.com/uploads/2024/04/def456.pdf"
        assert _detect_academic_year(url) == 2024

    def test_fallback_to_current_academic_year(self) -> None:
        url = "https://example.com/files/timetable.pdf"
        with patch("pipeline.main.date") as mock_date:
            mock_date.today.return_value = date(2026, 5, 15)
            assert _detect_academic_year(url) == 2026

    def test_academic_year_boundary_january_2026(self) -> None:
        url = "https://example.com/files/timetable.pdf"
        with patch("pipeline.main.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 15)
            assert _detect_academic_year(url) == 2025

    def test_academic_year_boundary_april_2026(self) -> None:
        url = "https://example.com/files/timetable.pdf"
        with patch("pipeline.main.date") as mock_date:
            mock_date.today.return_value = date(2026, 4, 1)
            assert _detect_academic_year(url) == 2026


# =============================================================================
# Test _handle_timetable()
# =============================================================================


class TestHandleTimetable:
    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.extract_courses_from_pdf")
    def test_normal_case_saves_raw_json(
        self, mock_extract: Mock, mock_update_status: Mock
    ) -> None:
        """Normal: courses extracted → saved as raw_json, status='extracted', NOT upserted."""
        course1 = Mock(model_dump=Mock(return_value={"code": "smab020161", "name": "Test"}))
        course2 = Mock(model_dump=Mock(return_value={"code": "smab020162", "name": "Test2"}))
        mock_extract.return_value = [course1, course2]

        result = _handle_timetable(
            b"fake pdf",
            "https://example.com/uploads/2025/04/test.pdf",
            "ext123",
            "spring",
            False,
            2025,
        )

        assert result == 2
        # Must save raw_json with status='extracted'
        mock_update_status.assert_called_once()
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["count"] == 2
        assert call_kwargs["raw_json"]["courses"][0]["code"] == "smab020161"

    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.extract_courses_from_pdf")
    def test_no_courses_extracted(
        self, mock_extract: Mock, mock_update_status: Mock
    ) -> None:
        mock_extract.return_value = []

        result = _handle_timetable(
            b"fake pdf",
            "https://example.com/uploads/2025/04/test.pdf",
            "ext123",
            "spring",
            False,
            2025,
        )

        assert result == 0
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["count"] == 0

    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.extract_courses_from_pdf")
    def test_confirmed_fall_raw_json_includes_semester(
        self, mock_extract: Mock, mock_update_status: Mock
    ) -> None:
        """Confirmed fall: semester and is_tentative saved in raw_json, NOT immediately deleted."""
        course1 = Mock(model_dump=Mock(return_value={"code": "smab020161", "name": "Test"}))
        mock_extract.return_value = [course1]

        _handle_timetable(
            b"fake pdf",
            "https://example.com/uploads/2025/09/test.pdf",
            "ext123",
            Semester.FALL.value,
            False,
            2025,
        )

        # raw_json must contain the metadata for later use at approval
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["semester"] == "fall"
        assert call_kwargs["raw_json"]["is_tentative"] is False


# =============================================================================
# Test _handle_changelog()
# =============================================================================


class TestHandleChangelog:
    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.parse_changelog")
    def test_normal_case_saves_raw_json(
        self, mock_parse: Mock, mock_update_status: Mock
    ) -> None:
        """Normal: changes parsed → saved as raw_json, NOT applied immediately."""
        change1 = Mock(model_dump=Mock(return_value={"change_type": "create"}))
        change2 = Mock(model_dump=Mock(return_value={"change_type": "update"}))
        mock_parse.return_value = [change1, change2]

        _handle_changelog(
            b"fake pdf",
            "https://example.com/uploads/2025/04/changelog.pdf",
            "ext456",
            "spring",
            2025,
        )

        mock_parse.assert_called_once_with(b"fake pdf")
        mock_update_status.assert_called_once()
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["count"] == 2
        assert call_kwargs["raw_json"]["semester"] == "spring"
        assert call_kwargs["raw_json"]["academic_year"] == 2025

    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.parse_changelog")
    def test_no_changes_parsed(self, mock_parse: Mock, mock_update_status: Mock) -> None:
        mock_parse.return_value = []

        _handle_changelog(
            b"fake pdf",
            "https://example.com/uploads/2025/04/changelog.pdf",
            "ext456",
            "spring",
            2025,
        )

        mock_update_status.assert_called_once()
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["count"] == 0

    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.parse_changelog")
    def test_semester_str_none_defaults_to_spring(
        self, mock_parse: Mock, mock_update_status: Mock
    ) -> None:
        change1 = Mock(model_dump=Mock(return_value={"change_type": "create"}))
        mock_parse.return_value = [change1]

        _handle_changelog(
            b"fake pdf",
            "https://example.com/uploads/2025/04/changelog.pdf",
            "ext456",
            None,
            2025,
        )

        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["semester"] == "spring"


# =============================================================================
# Test _handle_advance_enrollment()
# =============================================================================


class TestHandleAdvanceEnrollment:
    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.extract_course_names")
    def test_normal_case_saves_raw_json(
        self, mock_extract_names: Mock, mock_update_status: Mock
    ) -> None:
        """Normal: names extracted → saved as raw_json, flags NOT updated immediately."""
        mock_extract_names.return_value = ["Course1", "Course2"]

        _handle_advance_enrollment(
            b"fake pdf",
            "https://example.com/uploads/2025/04/advance.pdf",
            "ext789",
            2025,
        )

        mock_extract_names.assert_called_once_with(b"fake pdf")
        # Must save raw_json
        mock_update_status.assert_called_once()
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["count"] == 2
        assert call_kwargs["raw_json"]["names"] == ["Course1", "Course2"]

    @patch("pipeline.main.update_extraction_status")
    @patch("pipeline.main.extract_course_names")
    def test_no_names_extracted(
        self, mock_extract_names: Mock, mock_update_status: Mock
    ) -> None:
        mock_extract_names.return_value = []

        _handle_advance_enrollment(
            b"fake pdf",
            "https://example.com/uploads/2025/04/advance.pdf",
            "ext789",
            2025,
        )

        mock_update_status.assert_called_once()
        call_kwargs = mock_update_status.call_args[1]
        assert call_kwargs["raw_json"]["count"] == 0


# =============================================================================
# Test run_pipeline()
# =============================================================================


class TestRunPipeline:
    @patch("pipeline.main.get_pending_extractions")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_no_updates_returns_early(
        self, mock_check_updates: Mock, mock_validate: Mock, mock_get_pending: Mock
    ) -> None:
        mock_check_updates.return_value = []
        mock_get_pending.return_value = []

        run_pipeline()

        mock_validate.assert_called_once()
        mock_check_updates.assert_called_once()

    @patch("pipeline.main._handle_timetable")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.get_pending_extractions")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_one_timetable_pdf_processed(
        self,
        mock_check_updates: Mock,
        mock_validate: Mock,
        mock_download_pdf: Mock,
        mock_get_pending: Mock,
        mock_compute_hash: Mock,
        mock_handle_timetable: Mock,
    ) -> None:
        """One timetable PDF → _handle_timetable called, no enrichment triggered."""
        pdf_bytes = b"fake pdf"
        mock_check_updates.return_value = [
            {
                "url": "https://example.com/uploads/2025/04/timetable.pdf",
                "label": "Timetable",
                "action": "added",
                "pdf_type": "timetable",
                "semester": "spring",
            }
        ]
        mock_download_pdf.return_value = pdf_bytes
        mock_compute_hash.return_value = "hash123"
        mock_get_pending.side_effect = [
            [
                {
                    "id": "ext123",
                    "pdf_url": "https://example.com/uploads/2025/04/timetable.pdf",
                    "pdf_hash": "hash123",
                    "pdf_type": "timetable",
                    "semester": "spring",
                }
            ],
            [],  # no remaining pending
        ]
        mock_handle_timetable.return_value = 5

        run_pipeline()

        mock_handle_timetable.assert_called_once()
        # Enricher should NOT be called automatically — only after admin approval

    @patch("pipeline.main._handle_changelog")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.get_pending_extractions")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_one_changelog_pdf_processed(
        self,
        mock_check_updates: Mock,
        mock_validate: Mock,
        mock_download_pdf: Mock,
        mock_get_pending: Mock,
        mock_compute_hash: Mock,
        mock_handle_changelog: Mock,
    ) -> None:
        pdf_bytes = b"fake pdf"
        mock_check_updates.return_value = [
            {
                "url": "https://example.com/uploads/2025/04/changelog.pdf",
                "label": "Changelog",
                "action": "added",
                "pdf_type": "changelog",
                "semester": "spring",
            }
        ]
        mock_download_pdf.return_value = pdf_bytes
        mock_compute_hash.return_value = "hash456"
        mock_get_pending.side_effect = [
            [
                {
                    "id": "ext456",
                    "pdf_url": "https://example.com/uploads/2025/04/changelog.pdf",
                    "pdf_hash": "hash456",
                    "pdf_type": "changelog",
                    "semester": "spring",
                }
            ],
            [],
        ]

        run_pipeline()

        mock_handle_changelog.assert_called_once()

    @patch("pipeline.main._handle_advance_enrollment")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.get_pending_extractions")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_one_advance_enrollment_pdf_processed(
        self,
        mock_check_updates: Mock,
        mock_validate: Mock,
        mock_download_pdf: Mock,
        mock_get_pending: Mock,
        mock_compute_hash: Mock,
        mock_handle_advance_enrollment: Mock,
    ) -> None:
        pdf_bytes = b"fake pdf"
        mock_check_updates.return_value = [
            {
                "url": "https://example.com/uploads/2025/04/advance.pdf",
                "label": "Advance Enrollment",
                "action": "added",
                "pdf_type": "advance_enrollment",
                "semester": None,
            }
        ]
        mock_download_pdf.return_value = pdf_bytes
        mock_compute_hash.return_value = "hash789"
        mock_get_pending.side_effect = [
            [
                {
                    "id": "ext789",
                    "pdf_url": "https://example.com/uploads/2025/04/advance.pdf",
                    "pdf_hash": "hash789",
                    "pdf_type": "advance_enrollment",
                    "semester": None,
                }
            ],
            [],
        ]

        run_pipeline()

        mock_handle_advance_enrollment.assert_called_once()

    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.get_pending_extractions")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_download_failure_continues_to_next_pdf(
        self,
        mock_check_updates: Mock,
        mock_validate: Mock,
        mock_download_pdf: Mock,
        mock_get_pending: Mock,
        mock_compute_hash: Mock,
    ) -> None:
        mock_check_updates.return_value = [
            {
                "url": "https://example.com/uploads/2025/04/timetable1.pdf",
                "label": "Timetable",
                "action": "added",
                "pdf_type": "timetable",
                "semester": "spring",
            },
            {
                "url": "https://example.com/uploads/2025/04/timetable2.pdf",
                "label": "Timetable",
                "action": "added",
                "pdf_type": "timetable",
                "semester": "fall",
            },
        ]
        mock_download_pdf.side_effect = Exception("Network error")
        mock_get_pending.return_value = []

        run_pipeline()  # should not raise

        assert mock_download_pdf.call_count == 2

    @patch("pipeline.main._handle_timetable")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.get_pending_extractions")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_no_matching_extraction_record_skipped(
        self,
        mock_check_updates: Mock,
        mock_validate: Mock,
        mock_download_pdf: Mock,
        mock_get_pending: Mock,
        mock_compute_hash: Mock,
        mock_handle_timetable: Mock,
    ) -> None:
        pdf_bytes = b"fake pdf"
        mock_check_updates.return_value = [
            {
                "url": "https://example.com/uploads/2025/04/timetable.pdf",
                "label": "Timetable",
                "action": "added",
                "pdf_type": "timetable",
                "semester": "spring",
            }
        ]
        mock_download_pdf.return_value = pdf_bytes
        mock_compute_hash.return_value = "hash123"
        mock_get_pending.return_value = []

        run_pipeline()

        mock_handle_timetable.assert_not_called()

    @patch("pipeline.main._handle_timetable")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.get_pending_extractions")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_semester_both_converted_to_none(
        self,
        mock_check_updates: Mock,
        mock_validate: Mock,
        mock_download_pdf: Mock,
        mock_get_pending: Mock,
        mock_compute_hash: Mock,
        mock_handle_timetable: Mock,
    ) -> None:
        """semester='both' → converted to None internally."""
        pdf_bytes = b"fake pdf"
        mock_check_updates.return_value = [
            {
                "url": "https://example.com/uploads/2025/04/timetable.pdf",
                "label": "Timetable",
                "action": "added",
                "pdf_type": "timetable",
                "semester": "both",
            }
        ]
        mock_download_pdf.return_value = pdf_bytes
        mock_compute_hash.return_value = "hash123"
        mock_get_pending.side_effect = [
            [
                {
                    "id": "ext123",
                    "pdf_url": "https://example.com/uploads/2025/04/timetable.pdf",
                    "pdf_hash": "hash123",
                    "pdf_type": "timetable",
                    "semester": "both",
                }
            ],
            [],
        ]

        run_pipeline()

        call_args = mock_handle_timetable.call_args
        # semester_str should be None, not "both"
        assert call_args[0][3] is None
