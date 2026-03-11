import hashlib
import unittest
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

from ..monitor import (
    fetch_page,
    download_pdf,
    extract_pdf_links,
    compute_hash,
    check_for_updates,
    main,
    PdfLink,
)


# =============================================================================
# Test PdfLink dataclass
# =============================================================================


class TestPdfLink:
    """Test PdfLink dataclass."""

    def test_creation(self) -> None:
        """Should create a PdfLink with url and label."""
        link = PdfLink(url="https://example.com/file.pdf", label="Test PDF")
        assert link.url == "https://example.com/file.pdf"
        assert link.label == "Test PDF"

    def test_equality(self) -> None:
        """PdfLinks with same values should be equal."""
        link1 = PdfLink(url="https://example.com/file.pdf", label="Test")
        link2 = PdfLink(url="https://example.com/file.pdf", label="Test")
        assert link1 == link2


# =============================================================================
# Test fetch_page()
# =============================================================================


class TestFetchPage:
    """Test fetch_page() function."""

    @patch("requests.get")
    def test_fetch_page_success(self, mock_get) -> None:
        """Should return HTML content on success."""
        mock_response = Mock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_page("https://example.com")

        assert result == "<html><body>Test</body></html>"
        mock_get.assert_called_once_with("https://example.com", timeout=30)

    @patch("requests.get")
    def test_fetch_page_timeout(self, mock_get) -> None:
        """Should raise TimeoutError when request times out."""
        mock_get.side_effect = requests.Timeout("Connection timeout")

        with pytest.raises(requests.Timeout):
            fetch_page("https://example.com")

    @patch("requests.get")
    def test_fetch_page_http_error(self, mock_get) -> None:
        """Should raise HTTPError on 4xx/5xx responses."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            fetch_page("https://example.com")

    @patch("requests.get")
    def test_fetch_page_connection_error(self, mock_get) -> None:
        """Should raise ConnectionError when network is unavailable."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        with pytest.raises(requests.ConnectionError):
            fetch_page("https://example.com")


# =============================================================================
# Test download_pdf()
# =============================================================================


class TestDownloadPdf:
    """Test download_pdf() function."""

    @patch("requests.get")
    def test_download_pdf_success(self, mock_get) -> None:
        """Should return PDF bytes on success."""
        pdf_content = b"%PDF-1.4\n%fake pdf content"
        mock_response = Mock()
        mock_response.content = pdf_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = download_pdf("https://example.com/file.pdf")

        assert result == pdf_content
        mock_get.assert_called_once_with("https://example.com/file.pdf", timeout=60)

    @patch("requests.get")
    def test_download_pdf_timeout(self, mock_get) -> None:
        """Should raise TimeoutError when download times out."""
        mock_get.side_effect = requests.Timeout("Download timeout")

        with pytest.raises(requests.Timeout):
            download_pdf("https://example.com/file.pdf")

    @patch("requests.get")
    def test_download_pdf_http_error(self, mock_get) -> None:
        """Should raise HTTPError on non-2xx responses."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            download_pdf("https://example.com/file.pdf")

    @patch("requests.get")
    def test_download_pdf_different_sizes(self, mock_get) -> None:
        """Should handle PDFs of different sizes."""
        small_pdf = b"%PDF-1.4"
        large_pdf = b"%PDF-1.4" + b"x" * 10000

        # Test small PDF
        mock_response = Mock()
        mock_response.content = small_pdf
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = download_pdf("https://example.com/small.pdf")
        assert len(result) == len(small_pdf)

        # Test large PDF
        mock_response.content = large_pdf
        result = download_pdf("https://example.com/large.pdf")
        assert len(result) == len(large_pdf)


# =============================================================================
# Test extract_pdf_links()
# =============================================================================


class TestExtractPdfLinks:
    """Test extract_pdf_links() function."""

    # Realistic HTML snippet from the task description
    REALISTIC_HTML = """
    <section>
    <h2>【大学院】 総合理工学研究科</h2>
    <details><summary>■前期■</summary>
    <a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/03/front.pdf">〈総合理工学研究科〉全専攻 前期 授業時間表</a>
    </details>
    <details open=""><summary>■後期■</summary>
    <a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/09/back.pdf">〈総合理工学研究科〉全専攻 後期 授業時間表</a>
    </details>
    <a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/04/changes.pdf">〈総合理工学研究科〉授業時間表変更一覧</a>
    </section>
    <section>
    <h2>【学部】 理工学部</h2>
    <a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/03/undergrad.pdf">〈理工学部〉前期 授業時間表</a>
    </section>
    """

    def test_extract_pdf_links_with_filter(self) -> None:
        """Should extract PDF links matching the filter text."""
        links = extract_pdf_links(self.REALISTIC_HTML)

        assert len(links) == 3
        assert all(link.url.endswith(".pdf") for link in links)
        assert "総合理工学研究科" in links[0].label
        assert "総合理工学研究科" in links[1].label
        assert "総合理工学研究科" in links[2].label

    def test_extract_pdf_links_without_filter(self) -> None:
        """Should extract all PDF links when filter is empty."""
        links = extract_pdf_links(self.REALISTIC_HTML, filter_text="")

        assert len(links) == 4  # Including undergrad
        urls = [link.url for link in links]
        assert "https://www.asc.tcu.ac.jp/wp-content/uploads/2025/03/undergrad.pdf" in urls

    def test_extract_pdf_links_non_matching_filter(self) -> None:
        """Should exclude links that don't contain filter text."""
        links = extract_pdf_links(self.REALISTIC_HTML, filter_text="理工学部")

        assert len(links) == 1
        assert "理工学部" in links[0].label

    def test_extract_pdf_links_non_pdf_ignored(self) -> None:
        """Should ignore non-PDF links."""
        html = """
        <section>
        <a href="https://example.com/page.html">PDF Link Label with 総合理工学研究科</a>
        <a href="https://example.com/file.pdf">〈総合理工学研究科〉Real PDF</a>
        </section>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://example.com/file.pdf"

    def test_extract_pdf_links_duplicate_deduplication(self) -> None:
        """Should remove duplicate URLs (keep first occurrence)."""
        html = """
        <section>
        <a href="https://example.com/file.pdf">〈総合理工学研究科〉First</a>
        <a href="https://example.com/file.pdf">〈総合理工学研究科〉Second</a>
        </section>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].label == "〈総合理工学研究科〉First"

    def test_extract_pdf_links_protocol_relative_url(self) -> None:
        """Should convert protocol-relative URLs to https."""
        html = """
        <section>
        <a href="//cdn.example.com/file.pdf">〈総合理工学研究科〉PDF</a>
        </section>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://cdn.example.com/file.pdf"

    def test_extract_pdf_links_relative_url(self) -> None:
        """Should convert relative URLs to absolute."""
        html = """
        <section>
        <a href="/wp-content/uploads/file.pdf">〈総合理工学研究科〉PDF</a>
        </section>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://www.asc.tcu.ac.jp/wp-content/uploads/file.pdf"

    def test_extract_pdf_links_empty_page(self) -> None:
        """Should return empty list when no PDF links found."""
        html = "<section><h2>No PDFs here</h2><p>Just text</p></section>"
        links = extract_pdf_links(html)

        assert links == []

    def test_extract_pdf_links_no_matching_filter(self) -> None:
        """Should return empty list when no links match filter."""
        html = """
        <section>
        <a href="https://example.com/file.pdf">Other Department PDF</a>
        </section>
        """
        links = extract_pdf_links(html)

        assert links == []

    def test_extract_pdf_links_case_insensitive_pdf_check(self) -> None:
        """Should recognize .PDF (uppercase) as PDF link."""
        html = """
        <section>
        <a href="https://example.com/file.PDF">〈総合理工学研究科〉PDF</a>
        </section>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://example.com/file.PDF"

    def test_extract_pdf_links_preserves_order(self) -> None:
        """Should preserve the order of links as they appear in HTML."""
        html = """
        <section>
        <a href="https://example.com/first.pdf">〈総合理工学研究科〉First</a>
        <a href="https://example.com/second.pdf">〈総合理工学研究科〉Second</a>
        <a href="https://example.com/third.pdf">〈総合理工学研究科〉Third</a>
        </section>
        """
        links = extract_pdf_links(html)

        assert len(links) == 3
        assert links[0].label == "〈総合理工学研究科〉First"
        assert links[1].label == "〈総合理工学研究科〉Second"
        assert links[2].label == "〈総合理工学研究科〉Third"

    def test_extract_pdf_links_nested_html(self) -> None:
        """Should extract links from nested HTML elements."""
        html = """
        <div>
            <section>
                <details>
                    <summary>Details</summary>
                    <a href="https://example.com/nested.pdf">〈総合理工学研究科〉Nested</a>
                </details>
            </section>
        </div>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://example.com/nested.pdf"


# =============================================================================
# Test compute_hash()
# =============================================================================


class TestComputeHash:
    """Test compute_hash() function."""

    def test_compute_hash_basic(self) -> None:
        """Should compute SHA-256 hash of data."""
        data = b"test data"
        result = compute_hash(data)

        expected = hashlib.sha256(data).hexdigest()
        assert result == expected

    def test_compute_hash_deterministic(self) -> None:
        """Should return same hash for same data."""
        data = b"test data"
        hash1 = compute_hash(data)
        hash2 = compute_hash(data)

        assert hash1 == hash2

    def test_compute_hash_different_data(self) -> None:
        """Should return different hash for different data."""
        hash1 = compute_hash(b"data1")
        hash2 = compute_hash(b"data2")

        assert hash1 != hash2

    def test_compute_hash_empty_data(self) -> None:
        """Should handle empty data."""
        result = compute_hash(b"")
        expected = hashlib.sha256(b"").hexdigest()

        assert result == expected

    def test_compute_hash_large_data(self) -> None:
        """Should handle large data."""
        data = b"x" * 1000000  # 1MB
        result = compute_hash(data)

        assert len(result) == 64  # SHA-256 hex is 64 chars
        assert isinstance(result, str)

    def test_compute_hash_pdf_like_data(self) -> None:
        """Should hash PDF-like content correctly."""
        pdf_data = b"%PDF-1.4\n%fake content" + b"x" * 1000
        result = compute_hash(pdf_data)

        assert len(result) == 64
        assert isinstance(result, str)


# =============================================================================
# Test check_for_updates()
# =============================================================================


class TestCheckForUpdates:
    """Test check_for_updates() function."""

    REALISTIC_HTML = """
    <section>
    <h2>【大学院】 総合理工学研究科</h2>
    <a href="https://example.com/front.pdf">〈総合理工学研究科〉前期</a>
    <a href="https://example.com/back.pdf">〈総合理工学研究科〉後期</a>
    </section>
    """

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.db.get_stored_pdf_links")
    @patch("pipeline.db.upsert_pdf_link")
    @patch("pipeline.db.create_extraction")
    def test_check_for_updates_new_pdf(
        self,
        mock_create_extraction,
        mock_upsert_pdf_link,
        mock_get_stored,
        mock_download,
        mock_fetch,
    ) -> None:
        """Should detect new PDF and queue for extraction."""
        mock_fetch.return_value = self.REALISTIC_HTML
        mock_download.side_effect = [b"content1", b"content2"]
        mock_get_stored.return_value = {}  # No stored links

        result = check_for_updates()

        assert len(result) == 2
        assert result[0]["action"] == "new"
        assert result[1]["action"] == "new"
        assert mock_create_extraction.call_count == 2
        assert mock_upsert_pdf_link.call_count == 2

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.db.get_stored_pdf_links")
    @patch("pipeline.db.upsert_pdf_link")
    @patch("pipeline.db.create_extraction")
    def test_check_for_updates_changed_pdf(
        self,
        mock_create_extraction,
        mock_upsert_pdf_link,
        mock_get_stored,
        mock_download,
        mock_fetch,
    ) -> None:
        """Should detect changed PDF (same URL, different hash)."""
        mock_fetch.return_value = self.REALISTIC_HTML
        old_hash = compute_hash(b"old content")
        mock_download.return_value = b"new content"
        mock_get_stored.return_value = {
            "https://example.com/front.pdf": {"hash": old_hash},
            "https://example.com/back.pdf": {"hash": old_hash},
        }

        result = check_for_updates()

        assert len(result) == 2
        assert all(r["action"] == "changed" for r in result)
        assert mock_create_extraction.call_count == 2

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.db.get_stored_pdf_links")
    @patch("pipeline.db.upsert_pdf_link")
    @patch("pipeline.db.create_extraction")
    def test_check_for_updates_no_changes(
        self,
        mock_create_extraction,
        mock_upsert_pdf_link,
        mock_get_stored,
        mock_download,
        mock_fetch,
    ) -> None:
        """Should not queue PDFs with unchanged hash."""
        mock_fetch.return_value = self.REALISTIC_HTML
        pdf_content = b"unchanged content"
        pdf_hash = compute_hash(pdf_content)
        mock_download.return_value = pdf_content
        mock_get_stored.return_value = {
            "https://example.com/front.pdf": {"hash": pdf_hash},
            "https://example.com/back.pdf": {"hash": pdf_hash},
        }

        result = check_for_updates()

        assert result == []
        assert mock_create_extraction.call_count == 0
        assert mock_upsert_pdf_link.call_count == 0

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.db.get_stored_pdf_links")
    @patch("pipeline.db.upsert_pdf_link")
    @patch("pipeline.db.create_extraction")
    def test_check_for_updates_mixed_scenario(
        self,
        mock_create_extraction,
        mock_upsert_pdf_link,
        mock_get_stored,
        mock_download,
        mock_fetch,
    ) -> None:
        """Should handle mixed scenario: new, changed, unchanged."""
        html = """
        <section>
        <a href="https://example.com/new.pdf">〈総合理工学研究科〉New</a>
        <a href="https://example.com/changed.pdf">〈総合理工学研究科〉Changed</a>
        <a href="https://example.com/unchanged.pdf">〈総合理工学研究科〉Unchanged</a>
        </section>
        """
        mock_fetch.return_value = html
        unchanged_hash = compute_hash(b"unchanged")
        mock_download.side_effect = [
            b"new content",
            b"changed content",
            b"unchanged",
        ]
        mock_get_stored.return_value = {
            "https://example.com/changed.pdf": {"hash": unchanged_hash},
            "https://example.com/unchanged.pdf": {"hash": unchanged_hash},
        }

        result = check_for_updates()

        assert len(result) == 2
        actions = [r["action"] for r in result]
        assert "new" in actions
        assert "changed" in actions
        assert mock_create_extraction.call_count == 2

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.db.get_stored_pdf_links")
    def test_check_for_updates_no_links_found(
        self,
        mock_get_stored,
        mock_fetch,
    ) -> None:
        """Should return empty list when no PDF links found."""
        mock_fetch.return_value = "<section><p>No PDFs</p></section>"
        mock_get_stored.return_value = {}

        result = check_for_updates()

        assert result == []

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.db.get_stored_pdf_links")
    @patch("pipeline.db.upsert_pdf_link")
    @patch("pipeline.db.create_extraction")
    def test_check_for_updates_return_structure(
        self,
        mock_create_extraction,
        mock_upsert_pdf_link,
        mock_get_stored,
        mock_download,
        mock_fetch,
    ) -> None:
        """Should return correct structure with url, label, action."""
        mock_fetch.return_value = self.REALISTIC_HTML
        mock_download.return_value = b"content"
        mock_get_stored.return_value = {}

        result = check_for_updates()

        assert len(result) > 0
        for item in result:
            assert "url" in item
            assert "label" in item
            assert "action" in item
            assert item["action"] in ["new", "changed"]
            assert isinstance(item["url"], str)
            assert isinstance(item["label"], str)

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.config.Config.validate")
    def test_check_for_updates_uses_custom_url(
        self,
        mock_validate,
        mock_fetch,
    ) -> None:
        """Should accept custom target URL."""
        mock_fetch.return_value = "<section></section>"

        check_for_updates(target_url="https://custom.example.com")

        mock_fetch.assert_called_once_with("https://custom.example.com")

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.db.get_stored_pdf_links")
    @patch("pipeline.db.upsert_pdf_link")
    @patch("pipeline.db.create_extraction")
    def test_check_for_updates_calls_db_functions(
        self,
        mock_create_extraction,
        mock_upsert_pdf_link,
        mock_get_stored,
        mock_download,
        mock_fetch,
    ) -> None:
        """Should call db functions to persist and queue."""
        mock_fetch.return_value = self.REALISTIC_HTML
        mock_download.return_value = b"pdf content"
        mock_get_stored.return_value = {}

        check_for_updates()

        # Verify db functions were called
        assert mock_upsert_pdf_link.called
        assert mock_create_extraction.called


# =============================================================================
# Test main()
# =============================================================================


class TestMain:
    """Test main() function."""

    @patch("pipeline.monitor.check_for_updates")
    @patch("pipeline.config.Config.validate")
    def test_main_with_no_updates(self, mock_validate, mock_check) -> None:
        """Should call check_for_updates and handle no results."""
        mock_check.return_value = []

        main()

        mock_validate.assert_called_once()
        mock_check.assert_called_once()

    @patch("pipeline.monitor.check_for_updates")
    @patch("pipeline.config.Config.validate")
    def test_main_with_updates(self, mock_validate, mock_check) -> None:
        """Should call check_for_updates and handle results."""
        mock_check.return_value = [
            {"url": "https://example.com/file1.pdf", "label": "Test 1", "action": "new"},
            {"url": "https://example.com/file2.pdf", "label": "Test 2", "action": "changed"},
        ]

        main()

        mock_validate.assert_called_once()
        mock_check.assert_called_once()

    @patch("pipeline.monitor.check_for_updates")
    @patch("pipeline.config.Config.validate")
    def test_main_calls_config_validate(self, mock_validate, mock_check) -> None:
        """Should validate config before running."""
        mock_check.return_value = []

        main()

        mock_validate.assert_called_once()
        # check_for_updates should be called after validate
        mock_check.assert_called_once()

    @patch("pipeline.monitor.check_for_updates")
    @patch("pipeline.config.Config.validate")
    def test_main_validate_called_first(self, mock_validate, mock_check) -> None:
        """Should call validate before check_for_updates."""
        call_order = []
        mock_validate.side_effect = lambda: call_order.append("validate")
        mock_check.side_effect = lambda: call_order.append("check")
        mock_check.return_value = []

        main()

        assert call_order == ["validate", "check"]


# =============================================================================
# Integration-like tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow_realistic_html(self) -> None:
        """Should extract links from realistic HTML successfully."""
        html = """
        <section>
        <h2>【大学院】 総合理工学研究科</h2>
        <a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/03/front.pdf">〈総合理工学研究科〉全専攻 前期 授業時間表</a>
        <a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/09/back.pdf">〈総合理工学研究科〉全専攻 後期 授業時間表</a>
        </section>
        """

        links = extract_pdf_links(html)

        assert len(links) == 2
        for link in links:
            assert "総合理工学研究科" in link.label
            assert link.url.endswith(".pdf")

    def test_hash_consistency_with_pdf_content(self) -> None:
        """Should hash PDF content consistently."""
        pdf1 = b"%PDF-1.4\n%content"
        pdf2 = b"%PDF-1.4\n%content"
        pdf3 = b"%PDF-1.4\n%different"

        hash1 = compute_hash(pdf1)
        hash2 = compute_hash(pdf2)
        hash3 = compute_hash(pdf3)

        assert hash1 == hash2
        assert hash1 != hash3
