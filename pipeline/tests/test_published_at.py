from __future__ import annotations

from unittest.mock import Mock, patch
import pytest

from pipeline.adapters.http import (
    DownloadedPdf,
    fetch_bytes,
    fetch_pdf_with_metadata,
    parse_http_date,
)
from pipeline.services.extraction_service import (
    handle_advance_enrollment,
    handle_changelog,
    handle_timetable,
    process_extraction,
)
from pipeline.services.monitor_service import (
    extract_pdf_published_at,
    extract_published_at,
)


class TestHttpDateParsing:
    def test_parse_valid_rfc7231_date(self) -> None:
        """Should parse RFC 7231 date to JST ISO 8601 string."""
        raw = "Tue, 16 Sep 2025 07:28:44 GMT"
        # 07:28:44 GMT + 9 hours = 16:28:44 JST
        parsed = parse_http_date(raw)
        assert parsed == "2025-09-16T16:28:44+09:00"

    def test_parse_gmt_date_at_boundary(self) -> None:
        """Should roll over to next day when GMT + 9h crosses midnight."""
        raw = "Thu, 10 Sep 2026 18:00:00 GMT"
        # 18:00 GMT + 9 hours = 03:00 next day JST
        parsed = parse_http_date(raw)
        assert parsed == "2026-09-11T03:00:00+09:00"

    def test_parse_none_or_empty(self) -> None:
        assert parse_http_date(None) is None
        assert parse_http_date("") is None

    def test_parse_invalid_string(self) -> None:
        assert parse_http_date("not-a-date") is None


class TestDownloadedPdfAndFetchBytes:
    def test_downloaded_pdf_is_bytes_subclass(self) -> None:
        pdf = DownloadedPdf(b"fake pdf content", last_modified="2026-09-10T18:43:00+09:00")
        assert isinstance(pdf, bytes)
        assert pdf == b"fake pdf content"
        assert len(pdf) == len(b"fake pdf content")
        assert pdf.last_modified == "2026-09-10T18:43:00+09:00"

    @patch("requests.get")
    def test_fetch_bytes_returns_downloaded_pdf_with_last_modified(self, mock_get) -> None:
        mock_resp = Mock()
        mock_resp.content = b"%PDF-test"
        mock_resp.headers = {"Last-Modified": "Thu, 10 Sep 2026 09:43:48 GMT"}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = fetch_bytes("https://example.com/test.pdf")
        assert isinstance(result, DownloadedPdf)
        assert result == b"%PDF-test"
        assert result.last_modified == "2026-09-10T18:43:48+09:00"

    @patch("requests.get")
    def test_fetch_pdf_with_metadata_returns_tuple(self, mock_get) -> None:
        mock_resp = Mock()
        mock_resp.content = b"%PDF-test"
        mock_resp.headers = {"Last-Modified": "Thu, 10 Sep 2026 09:43:48 GMT"}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        content, last_modified = fetch_pdf_with_metadata("https://example.com/test.pdf")
        assert isinstance(content, bytes)
        assert content == b"%PDF-test"
        assert last_modified == "2026-09-10T18:43:48+09:00"


class TestExtractPublishedAtPriority:
    def test_last_modified_has_priority_over_pdf_moddate(self) -> None:
        """When Last-Modified is provided, it should be chosen over PDF metadata."""
        # Dummy PDF with ModDate 2025-09-12
        import io
        import pypdf
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_metadata({"/ModDate": "D:20250912125200+09'00'"})
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        # Check internal ModDate works
        internal_date = extract_pdf_published_at(pdf_bytes)
        assert internal_date is not None
        assert "2025-09-12" in internal_date

        # extract_published_at with Last-Modified
        last_modified = "2025-09-16T16:28:44+09:00"
        chosen = extract_published_at(pdf_bytes, last_modified_str=last_modified)
        assert chosen == "2025-09-16T16:28:44+09:00"

    def test_fallback_to_pdf_moddate_when_no_last_modified(self) -> None:
        import io
        import pypdf
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_metadata({"/ModDate": "D:20260415180900+09'00'"})
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        chosen = extract_published_at(pdf_bytes, last_modified_str=None)
        assert chosen is not None
        assert chosen.startswith("2026-04-15")

    def test_returns_none_when_neither_available(self) -> None:
        chosen = extract_published_at(b"not-a-pdf", last_modified_str=None)
        assert chosen is None


class TestExtractionServicePreservesPublishedAt:
    def test_handle_timetable_preserves_published_at(self) -> None:
        mock_update = Mock()
        mock_course = Mock()
        mock_course.model_dump.return_value = {"name": "Course 1"}
        mock_course.semester = None

        handle_timetable(
            pdf_bytes=b"dummy",
            pdf_url="https://example.com/test.pdf",
            extraction_id="ext-1",
            semester_str="spring",
            is_tentative=False,
            academic_year=2026,
            extract_courses_from_pdf=lambda _: [mock_course],
            update_extraction_status=mock_update,
            published_at="2026-04-15T18:11:13+09:00",
        )

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        raw_json = call_kwargs.get("raw_json", {})
        assert raw_json.get("published_at") == "2026-04-15T18:11:13+09:00"

    def test_handle_changelog_preserves_published_at(self) -> None:
        mock_update = Mock()
        mock_change = Mock()
        mock_change.model_dump.return_value = {"detail": "Change 1"}

        handle_changelog(
            pdf_bytes=b"dummy",
            pdf_url="https://example.com/test.pdf",
            extraction_id="ext-2",
            semester_str="spring",
            academic_year=2026,
            parse_changelog=lambda _: [mock_change],
            update_extraction_status=mock_update,
            published_at="2026-05-01T16:20:00+09:00",
        )

        mock_update.assert_called_once()
        raw_json = mock_update.call_args[1].get("raw_json", {})
        assert raw_json.get("published_at") == "2026-05-01T16:20:00+09:00"

    def test_handle_advance_enrollment_preserves_published_at(self) -> None:
        mock_update = Mock()

        handle_advance_enrollment(
            pdf_bytes=b"dummy",
            pdf_url="https://example.com/test.pdf",
            extraction_id="ext-3",
            academic_year=2026,
            extract_course_names=lambda _: ["Adv Course 1"],
            update_extraction_status=mock_update,
            published_at="2026-03-26T14:52:00+09:00",
        )

        mock_update.assert_called_once()
        raw_json = mock_update.call_args[1].get("raw_json", {})
        assert raw_json.get("published_at") == "2026-03-26T14:52:00+09:00"
