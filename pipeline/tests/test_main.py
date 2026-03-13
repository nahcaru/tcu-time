from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest

from ..main import (
    _detect_academic_year,
    _handle_advance_enrollment,
    _handle_changelog,
    _handle_timetable,
    _run_enrichment,
    run_pipeline,
)
from ..models import PDFType, Semester


# =============================================================================
# Test _detect_academic_year()
# =============================================================================


class TestDetectAcademicYear:
    """Tests for _detect_academic_year function."""

    def test_detects_year_from_url_with_uploads_2025(self) -> None:
        """URL with /uploads/2025/ returns 2025."""
        url = "https://example.com/uploads/2025/04/abc123.pdf"
        assert _detect_academic_year(url) == 2025

    def test_detects_year_from_url_with_uploads_2024(self) -> None:
        """URL with /uploads/2024/04/ returns 2024."""
        url = "https://example.com/uploads/2024/04/def456.pdf"
        assert _detect_academic_year(url) == 2024

    def test_fallback_to_current_academic_year(self) -> None:
        """URL without uploads pattern falls back to current academic year."""
        url = "https://example.com/files/timetable.pdf"
        with patch("pipeline.main.date") as mock_date:
            mock_date.today.return_value = date(2026, 5, 15)
            assert _detect_academic_year(url) == 2026

    def test_academic_year_boundary_january_2026(self) -> None:
        """January 2026 returns 2025 (academic year starts April)."""
        url = "https://example.com/files/timetable.pdf"
        with patch("pipeline.main.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 15)
            assert _detect_academic_year(url) == 2025

    def test_academic_year_boundary_april_2026(self) -> None:
        """April 2026 returns 2026 (academic year starts April)."""
        url = "https://example.com/files/timetable.pdf"
        with patch("pipeline.main.date") as mock_date:
            mock_date.today.return_value = date(2026, 4, 1)
            assert _detect_academic_year(url) == 2026


# =============================================================================
# Test _handle_timetable()
# =============================================================================


class TestHandleTimetable:
    """Tests for _handle_timetable function."""

    @patch("pipeline.main.db")
    @patch("pipeline.extractor.extract_courses_from_pdf")
    @patch("pipeline.classifier.classify_pages")
    def test_normal_case_courses_extracted(
        self, mock_classify, mock_extract, mock_db
    ) -> None:
        """Normal case: courses extracted → upsert_courses called, status updated, returns course count."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/04/test.pdf"
        extraction_id = "ext123"
        semester_str = "spring"
        is_tentative = False
        academic_year = 2025

        mock_classify.return_value = [Mock(type="course_table_spring")]
        course1 = Mock(model_dump=Mock(return_value={"code": "smab020161", "name": "Test"}))
        course2 = Mock(model_dump=Mock(return_value={"code": "smab020162", "name": "Test2"}))
        mock_extract.return_value = [course1, course2]

        result = _handle_timetable(
            pdf_bytes, pdf_url, extraction_id, semester_str, is_tentative, academic_year
        )

        assert result == 2
        mock_classify.assert_called_once_with(pdf_bytes)
        mock_extract.assert_called_once()
        mock_db.upsert_courses.assert_called_once()
        mock_db.update_extraction_status.assert_called_once()

    @patch("pipeline.main.db")
    @patch("pipeline.extractor.extract_courses_from_pdf")
    @patch("pipeline.classifier.classify_pages")
    def test_no_courses_extracted(
        self, mock_classify, mock_extract, mock_db
    ) -> None:
        """No courses extracted → update_extraction_status called with empty data, returns 0."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/04/test.pdf"
        extraction_id = "ext123"
        semester_str = "spring"
        is_tentative = False
        academic_year = 2025

        mock_classify.return_value = []
        mock_extract.return_value = []

        result = _handle_timetable(
            pdf_bytes, pdf_url, extraction_id, semester_str, is_tentative, academic_year
        )

        assert result == 0
        mock_db.upsert_courses.assert_not_called()
        mock_db.update_extraction_status.assert_called_once()
        call_args = mock_db.update_extraction_status.call_args
        assert call_args[1]["raw_json"]["count"] == 0

    @patch("pipeline.main.db")
    @patch("pipeline.extractor.extract_courses_from_pdf")
    @patch("pipeline.classifier.classify_pages")
    def test_confirmed_fall_pdf_deletes_tentative_courses(
        self, mock_classify, mock_extract, mock_db
    ) -> None:
        """Confirmed fall PDF: semester_str='fall', is_tentative=False → db.delete_courses called before upsert."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/09/test.pdf"
        extraction_id = "ext123"
        semester_str = Semester.FALL.value
        is_tentative = False
        academic_year = 2025

        mock_classify.return_value = [Mock(type="course_table_fall")]
        course1 = Mock(model_dump=Mock(return_value={"code": "smab020161", "name": "Test"}))
        mock_extract.return_value = [course1]
        mock_db.delete_courses.return_value = 3

        _handle_timetable(
            pdf_bytes, pdf_url, extraction_id, semester_str, is_tentative, academic_year
        )

        mock_db.delete_courses.assert_called_once_with(academic_year=2025, is_tentative=True)
        mock_db.upsert_courses.assert_called_once()

    @patch("pipeline.main.db")
    @patch("pipeline.extractor.extract_courses_from_pdf")
    @patch("pipeline.classifier.classify_pages")
    def test_tentative_fall_pdf_does_not_delete(
        self, mock_classify, mock_extract, mock_db
    ) -> None:
        """Tentative flag True + fall → db.delete_courses NOT called."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/09/test.pdf"
        extraction_id = "ext123"
        semester_str = Semester.FALL.value
        is_tentative = True
        academic_year = 2025

        mock_classify.return_value = [Mock(type="course_table_fall")]
        course1 = Mock(model_dump=Mock(return_value={"code": "smab020161", "name": "Test"}))
        mock_extract.return_value = [course1]

        _handle_timetable(
            pdf_bytes, pdf_url, extraction_id, semester_str, is_tentative, academic_year
        )

        mock_db.delete_courses.assert_not_called()
        mock_db.upsert_courses.assert_called_once()


# =============================================================================
# Test _handle_changelog()
# =============================================================================


class TestHandleChangelog:
    """Tests for _handle_changelog function."""

    @patch("pipeline.main.db")
    @patch("pipeline.changelog.apply_changelog")
    @patch("pipeline.changelog.parse_changelog")
    def test_normal_case_changes_parsed(
        self, mock_parse, mock_apply, mock_db
    ) -> None:
        """Normal: changes parsed → apply_changelog called with correct semester and academic_year."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/04/changelog.pdf"
        extraction_id = "ext456"
        semester_str = "spring"
        academic_year = 2025

        change1 = Mock(model_dump=Mock(return_value={"change_type": "add"}))
        change2 = Mock(model_dump=Mock(return_value={"change_type": "modify"}))
        mock_parse.return_value = [change1, change2]

        _handle_changelog(pdf_bytes, pdf_url, extraction_id, semester_str, academic_year)

        mock_parse.assert_called_once_with(pdf_bytes)
        mock_apply.assert_called_once_with(
            [change1, change2],
            semester="spring",
            academic_year=2025,
        )
        mock_db.update_extraction_status.assert_called_once()

    @patch("pipeline.main.db")
    @patch("pipeline.changelog.apply_changelog")
    @patch("pipeline.changelog.parse_changelog")
    def test_no_changes_parsed(self, mock_parse, mock_apply, mock_db) -> None:
        """No changes → update_extraction_status called, apply_changelog NOT called."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/04/changelog.pdf"
        extraction_id = "ext456"
        semester_str = "spring"
        academic_year = 2025

        mock_parse.return_value = []

        _handle_changelog(pdf_bytes, pdf_url, extraction_id, semester_str, academic_year)

        mock_apply.assert_not_called()
        mock_db.update_extraction_status.assert_called_once()

    @patch("pipeline.main.db")
    @patch("pipeline.changelog.apply_changelog")
    @patch("pipeline.changelog.parse_changelog")
    def test_semester_str_none_defaults_to_spring(
        self, mock_parse, mock_apply, mock_db
    ) -> None:
        """semester_str is None → defaults to 'spring' in apply_changelog call."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/04/changelog.pdf"
        extraction_id = "ext456"
        semester_str = None
        academic_year = 2025

        change1 = Mock()
        mock_parse.return_value = [change1]

        _handle_changelog(pdf_bytes, pdf_url, extraction_id, semester_str, academic_year)

        mock_apply.assert_called_once()
        call_args = mock_apply.call_args
        assert call_args[1]["semester"] == "spring"


# =============================================================================
# Test _handle_advance_enrollment()
# =============================================================================


class TestHandleAdvanceEnrollment:
    """Tests for _handle_advance_enrollment function."""

    @patch("pipeline.main.db")
    @patch("pipeline.advance.update_flags")
    @patch("pipeline.advance.extract_course_names")
    def test_normal_case_names_extracted(
        self, mock_extract_names, mock_update_flags, mock_db
    ) -> None:
        """Normal: names extracted → update_flags called."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/04/advance.pdf"
        extraction_id = "ext789"
        academic_year = 2025

        mock_extract_names.return_value = ["Course1", "Course2"]

        _handle_advance_enrollment(pdf_bytes, pdf_url, extraction_id, academic_year)

        mock_extract_names.assert_called_once_with(pdf_bytes)
        mock_update_flags.assert_called_once_with(["Course1", "Course2"], 2025)
        mock_db.update_extraction_status.assert_called_once()

    @patch("pipeline.main.db")
    @patch("pipeline.advance.update_flags")
    @patch("pipeline.advance.extract_course_names")
    def test_no_names_extracted(
        self, mock_extract_names, mock_update_flags, mock_db
    ) -> None:
        """No names → update_flags NOT called."""
        pdf_bytes = b"fake pdf"
        pdf_url = "https://example.com/uploads/2025/04/advance.pdf"
        extraction_id = "ext789"
        academic_year = 2025

        mock_extract_names.return_value = []

        _handle_advance_enrollment(pdf_bytes, pdf_url, extraction_id, academic_year)

        mock_update_flags.assert_not_called()
        mock_db.update_extraction_status.assert_called_once()


# =============================================================================
# Test _run_enrichment()
# =============================================================================


class TestRunEnrichment:
    """Tests for _run_enrichment function."""

    @patch("pipeline.main.db")
    @patch("pipeline.enricher.enrich_courses")
    def test_no_courses_need_enrichment(self, mock_enrich, mock_db) -> None:
        """No courses → enrich_courses NOT called."""
        mock_db.get_courses_needing_enrichment.return_value = []

        _run_enrichment(2025)

        mock_enrich.assert_not_called()

    @patch("pipeline.main.db")
    @patch("pipeline.enricher.enrich_courses")
    def test_courses_exist_enrichment_called(self, mock_enrich, mock_db) -> None:
        """Courses exist → enrich_courses called."""
        course1 = Mock()
        course2 = Mock()
        mock_db.get_courses_needing_enrichment.return_value = [course1, course2]
        mock_enrich.return_value = (2, 0)

        _run_enrichment(2025)

        mock_enrich.assert_called_once_with([course1, course2], 2025)


# =============================================================================
# Test run_pipeline()
# =============================================================================


class TestRunPipeline:
    """Tests for run_pipeline function."""

    @patch("pipeline.main.db")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_no_updates_returns_early(self, mock_check_updates, mock_validate, mock_db) -> None:
        """No updates and no pending extractions → returns early, no processing."""
        mock_check_updates.return_value = []
        mock_db.get_pending_extractions.return_value = []

        run_pipeline()

        mock_validate.assert_called_once()
        mock_check_updates.assert_called_once()

    @patch("pipeline.main._run_enrichment")
    @patch("pipeline.main._handle_timetable")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_one_timetable_pdf_processed(
        self,
        mock_check_updates,
        mock_validate,
        mock_download_pdf,
        mock_db,
        mock_compute_hash,
        mock_handle_timetable,
        mock_run_enrichment,
    ) -> None:
        """One timetable PDF → _handle_timetable flow triggered."""
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
        mock_db.get_pending_extractions.side_effect = [
            [
                {
                    "id": "ext123",
                    "pdf_url": "https://example.com/uploads/2025/04/timetable.pdf",
                    "pdf_hash": "hash123",
                }
            ],
            [],  # step 1b: no remaining pending
        ]
        mock_handle_timetable.return_value = 5

        run_pipeline()

        mock_validate.assert_called_once()
        mock_check_updates.assert_called_once()
        mock_handle_timetable.assert_called_once()
        mock_run_enrichment.assert_called_once_with(2025)

    @patch("pipeline.main._run_enrichment")
    @patch("pipeline.main._handle_changelog")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_one_changelog_pdf_processed(
        self,
        mock_check_updates,
        mock_validate,
        mock_download_pdf,
        mock_db,
        mock_compute_hash,
        mock_handle_changelog,
        mock_run_enrichment,
    ) -> None:
        """One changelog PDF → _handle_changelog flow triggered."""
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
        mock_db.get_pending_extractions.side_effect = [
            [
                {
                    "id": "ext456",
                    "pdf_url": "https://example.com/uploads/2025/04/changelog.pdf",
                    "pdf_hash": "hash456",
                }
            ],
            [],  # step 1b: no remaining pending
        ]

        run_pipeline()

        mock_handle_changelog.assert_called_once()
        mock_run_enrichment.assert_called_once_with(2025)

    @patch("pipeline.main._run_enrichment")
    @patch("pipeline.main._handle_advance_enrollment")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_one_advance_enrollment_pdf_processed(
        self,
        mock_check_updates,
        mock_validate,
        mock_download_pdf,
        mock_db,
        mock_compute_hash,
        mock_handle_advance_enrollment,
        mock_run_enrichment,
    ) -> None:
        """One advance_enrollment PDF → _handle_advance_enrollment flow triggered."""
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
        mock_db.get_pending_extractions.side_effect = [
            [
                {
                    "id": "ext789",
                    "pdf_url": "https://example.com/uploads/2025/04/advance.pdf",
                    "pdf_hash": "hash789",
                }
            ],
            [],  # step 1b: no remaining pending
        ]

        run_pipeline()

        mock_handle_advance_enrollment.assert_called_once()
        mock_run_enrichment.assert_called_once_with(2025)

    @patch("pipeline.main._run_enrichment")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_download_failure_continues_to_next_pdf(
        self,
        mock_check_updates,
        mock_validate,
        mock_download_pdf,
        mock_db,
        mock_compute_hash,
        mock_run_enrichment,
    ) -> None:
        """Download failure → logged, continues to next PDF."""
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
        mock_db.get_pending_extractions.return_value = []

        run_pipeline()

        assert mock_download_pdf.call_count == 2
        mock_run_enrichment.assert_not_called()

    @patch("pipeline.main._run_enrichment")
    @patch("pipeline.main._handle_timetable")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_no_matching_extraction_record_skipped(
        self,
        mock_check_updates,
        mock_validate,
        mock_download_pdf,
        mock_db,
        mock_compute_hash,
        mock_handle_timetable,
        mock_run_enrichment,
    ) -> None:
        """No matching extraction record → skipped with warning."""
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
        mock_db.get_pending_extractions.return_value = []  # no match in step 1a, and no pending in step 1b

        run_pipeline()

        mock_handle_timetable.assert_not_called()

    @patch("pipeline.main._run_enrichment")
    @patch("pipeline.monitor.compute_hash")
    @patch("pipeline.main.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.config.Config.validate")
    @patch("pipeline.monitor.check_for_updates")
    def test_semester_both_converted_to_none(
        self,
        mock_check_updates,
        mock_validate,
        mock_download_pdf,
        mock_db,
        mock_compute_hash,
        mock_run_enrichment,
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
        mock_db.get_pending_extractions.side_effect = [
            [
                {
                    "id": "ext123",
                    "pdf_url": "https://example.com/uploads/2025/04/timetable.pdf",
                    "pdf_hash": "hash123",
                }
            ],
            [],  # step 1b: no remaining pending
        ]

        with patch("pipeline.main._handle_timetable") as mock_handle:
            run_pipeline()
            call_args = mock_handle.call_args
            # semester_str should be None, not "both"
            assert call_args[0][3] is None
