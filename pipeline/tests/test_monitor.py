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
    _iter_siblings_until,
    GRAD_SECTION_HEADER,
    GRAD_DEPARTMENT,
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
# Test extract_pdf_links() — structural HTML parsing
# =============================================================================


# HTML fixture matching the real structure at asc.tcu.ac.jp/6509/
REALISTIC_HTML = """\
<div id="main">
<section>
  <div class="header"><h3>【学部】 理工学部・建築都市デザイン学部</h3></div>
  <p><a href="https://example.com/undergrad_front.pdf">〈世田谷キャンパス〉全学科 前期 授業時間表</a></p>
  <p><a href="https://example.com/undergrad_back.pdf">〈世田谷キャンパス〉全学科 後期 授業時間表</a></p>
</section>
<section>
  <div class="header"><h3>【大学院】</h3></div>
  <h4>総合理工学研究科〈全専攻〉</h4>
  <h5>■前期■</h5>
  <p>
    <a href="https://example.com/grad_changes.pdf">【前期】授業時間表変更一覧</a>
    <span style="color: #ff0000;">(5/1更新)</span>
    <br/>
    <a href="https://example.com/grad_front.pdf">授業時間表</a>
  </p>
  <h5>■後期■</h5>
  <p>
    <a href="https://example.com/grad_back.pdf">授業時間表</a>
    <span style="color: #ff0000;">(9/16公開)</span>
  </p>
  <hr/>
  <h4>環境情報学研究科〈都市生活学専攻〉</h4>
  <h5>■前期■</h5>
  <p>
    <a href="https://example.com/env_front.pdf">授業時間表</a>
  </p>
  <h5>■後期■</h5>
  <p>
    <a href="https://example.com/env_back.pdf">授業時間表</a>
  </p>
</section>
<section>
  <div class="header"><h3>【先行履修】</h3></div>
  <p><a href="https://example.com/advance.pdf">先行履修についての案内</a></p>
</section>
</div>
"""


class TestExtractPdfLinks:
    """Test extract_pdf_links() with structural HTML parsing."""

    def test_extracts_correct_links_from_realistic_html(self) -> None:
        """Should extract exactly the 3 timetable PDFs for 総合理工学研究科."""
        links = extract_pdf_links(REALISTIC_HTML)

        assert len(links) == 3
        urls = [link.url for link in links]
        assert "https://example.com/grad_changes.pdf" in urls
        assert "https://example.com/grad_front.pdf" in urls
        assert "https://example.com/grad_back.pdf" in urls

    def test_excludes_other_department_links(self) -> None:
        """Should NOT include 環境情報学研究科 links."""
        links = extract_pdf_links(REALISTIC_HTML)
        urls = [link.url for link in links]

        assert "https://example.com/env_front.pdf" not in urls
        assert "https://example.com/env_back.pdf" not in urls

    def test_excludes_undergrad_links(self) -> None:
        """Should NOT include undergraduate links."""
        links = extract_pdf_links(REALISTIC_HTML)
        urls = [link.url for link in links]

        assert "https://example.com/undergrad_front.pdf" not in urls
        assert "https://example.com/undergrad_back.pdf" not in urls

    def test_labels_prefixed_with_department(self) -> None:
        """Should prefix all labels with 〈総合理工学研究科〉."""
        links = extract_pdf_links(REALISTIC_HTML)

        for link in links:
            assert link.label.startswith("〈総合理工学研究科〉")

    def test_label_content(self) -> None:
        """Should preserve the original link text after the department prefix."""
        links = extract_pdf_links(REALISTIC_HTML)
        labels = [link.label for link in links]

        assert "〈総合理工学研究科〉【前期】授業時間表変更一覧" in labels
        assert "〈総合理工学研究科〉授業時間表" in labels

    def test_preserves_order(self) -> None:
        """Should preserve the order of links as they appear in HTML."""
        links = extract_pdf_links(REALISTIC_HTML)

        assert links[0].url == "https://example.com/grad_changes.pdf"
        assert links[1].url == "https://example.com/grad_front.pdf"
        assert links[2].url == "https://example.com/grad_back.pdf"

    def test_custom_department(self) -> None:
        """Should extract links for a different department when specified."""
        links = extract_pdf_links(
            REALISTIC_HTML, department="環境情報学研究科"
        )

        assert len(links) == 2
        urls = [link.url for link in links]
        assert "https://example.com/env_front.pdf" in urls
        assert "https://example.com/env_back.pdf" in urls

    def test_custom_section_header(self) -> None:
        """Should look inside a different section when header is overridden."""
        links = extract_pdf_links(
            REALISTIC_HTML,
            section_header="先行履修",
            department="",  # empty matches any h4 — but there's no h4
        )
        # 先行履修 section has no <h4>, so no department match
        assert links == []

    def test_no_matching_section(self) -> None:
        """Should return empty list when section header not found."""
        html = '<div id="main"><section><h3>Something Else</h3></section></div>'
        links = extract_pdf_links(html)
        assert links == []

    def test_no_matching_department(self) -> None:
        """Should return empty list when department h4 not found."""
        html = """\
        <div id="main">
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>Other Department</h4>
          <p><a href="https://example.com/file.pdf">PDF</a></p>
        </section>
        </div>
        """
        links = extract_pdf_links(html)
        assert links == []

    def test_non_pdf_links_ignored(self) -> None:
        """Should ignore non-PDF links in the department section."""
        html = """\
        <div id="main">
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>総合理工学研究科〈全専攻〉</h4>
          <p>
            <a href="https://example.com/page.html">Not a PDF</a>
            <a href="https://example.com/file.pdf">A PDF</a>
          </p>
          <hr/>
        </section>
        </div>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://example.com/file.pdf"

    def test_duplicate_urls_deduplicated(self) -> None:
        """Should remove duplicate URLs, keeping the first occurrence."""
        html = """\
        <div id="main">
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>総合理工学研究科〈全専攻〉</h4>
          <p><a href="https://example.com/file.pdf">First</a></p>
          <p><a href="https://example.com/file.pdf">Second</a></p>
          <hr/>
        </section>
        </div>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert "First" in links[0].label

    def test_protocol_relative_url(self) -> None:
        """Should convert protocol-relative URLs to https."""
        html = """\
        <div id="main">
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>総合理工学研究科〈全専攻〉</h4>
          <p><a href="//cdn.example.com/file.pdf">PDF</a></p>
          <hr/>
        </section>
        </div>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://cdn.example.com/file.pdf"

    def test_relative_url(self) -> None:
        """Should convert relative URLs to absolute."""
        html = """\
        <div id="main">
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>総合理工学研究科〈全専攻〉</h4>
          <p><a href="/wp-content/uploads/file.pdf">PDF</a></p>
          <hr/>
        </section>
        </div>
        """
        links = extract_pdf_links(html)

        assert len(links) == 1
        assert links[0].url == "https://www.asc.tcu.ac.jp/wp-content/uploads/file.pdf"

    def test_case_insensitive_pdf_extension(self) -> None:
        """Should recognize .PDF (uppercase) as PDF link."""
        html = """\
        <div id="main">
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>総合理工学研究科〈全専攻〉</h4>
          <p><a href="https://example.com/file.PDF">PDF</a></p>
          <hr/>
        </section>
        </div>
        """
        links = extract_pdf_links(html)
        assert len(links) == 1

    def test_empty_page(self) -> None:
        """Should return empty list when page has no sections."""
        html = "<div id='main'><p>Nothing here</p></div>"
        links = extract_pdf_links(html)
        assert links == []

    def test_fallback_without_div_main(self) -> None:
        """Should still work if div#main is absent (falls back to whole doc)."""
        html = """\
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>総合理工学研究科〈全専攻〉</h4>
          <p><a href="https://example.com/file.pdf">授業時間表</a></p>
          <hr/>
        </section>
        """
        links = extract_pdf_links(html)
        assert len(links) == 1
        assert links[0].url == "https://example.com/file.pdf"

    def test_stops_at_hr_boundary(self) -> None:
        """Should stop collecting at <hr/> before next department."""
        links = extract_pdf_links(REALISTIC_HTML)
        urls = [link.url for link in links]
        # env_ links are after <hr/>, should not be included
        assert not any("env_" in url for url in urls)

    def test_stops_at_h4_boundary(self) -> None:
        """Should stop collecting at next <h4> even without <hr/>."""
        html = """\
        <div id="main">
        <section>
          <div class="header"><h3>【大学院】</h3></div>
          <h4>総合理工学研究科〈全専攻〉</h4>
          <p><a href="https://example.com/target.pdf">Target</a></p>
          <h4>Other Department</h4>
          <p><a href="https://example.com/other.pdf">Other</a></p>
        </section>
        </div>
        """
        links = extract_pdf_links(html)
        assert len(links) == 1
        assert links[0].url == "https://example.com/target.pdf"


# =============================================================================
# Test _iter_siblings_until()
# =============================================================================


class TestIterSiblingsUntil:
    """Test the _iter_siblings_until helper."""

    def test_yields_siblings_until_stop_tag(self) -> None:
        """Should yield siblings until a stop tag is encountered."""
        from bs4 import BeautifulSoup

        html = "<div><h4>Start</h4><p>One</p><p>Two</p><hr/><p>Three</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        h4 = soup.find("h4")
        siblings = list(_iter_siblings_until(h4, {"hr"}))

        assert len(siblings) == 2
        assert siblings[0].name == "p"
        assert siblings[1].name == "p"

    def test_yields_all_if_no_stop_tag(self) -> None:
        """Should yield all siblings if no stop tag is encountered."""
        from bs4 import BeautifulSoup

        html = "<div><h4>Start</h4><p>One</p><p>Two</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        h4 = soup.find("h4")
        siblings = list(_iter_siblings_until(h4, {"hr"}))

        assert len(siblings) == 2


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

    CHECK_FOR_UPDATES_HTML = REALISTIC_HTML

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
        mock_fetch.return_value = self.CHECK_FOR_UPDATES_HTML
        mock_download.side_effect = [b"content1", b"content2", b"content3"]
        mock_get_stored.return_value = {}  # No stored links

        result = check_for_updates()

        assert len(result) == 3
        assert all(r["action"] == "new" for r in result)
        assert mock_create_extraction.call_count == 3
        assert mock_upsert_pdf_link.call_count == 3

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
        mock_fetch.return_value = self.CHECK_FOR_UPDATES_HTML
        old_hash = compute_hash(b"old content")
        mock_download.return_value = b"new content"
        mock_get_stored.return_value = {
            "https://example.com/grad_changes.pdf": {"hash": old_hash},
            "https://example.com/grad_front.pdf": {"hash": old_hash},
            "https://example.com/grad_back.pdf": {"hash": old_hash},
        }

        result = check_for_updates()

        assert len(result) == 3
        assert all(r["action"] == "changed" for r in result)
        assert mock_create_extraction.call_count == 3

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
        mock_fetch.return_value = self.CHECK_FOR_UPDATES_HTML
        pdf_content = b"unchanged content"
        pdf_hash = compute_hash(pdf_content)
        mock_download.return_value = pdf_content
        mock_get_stored.return_value = {
            "https://example.com/grad_changes.pdf": {"hash": pdf_hash},
            "https://example.com/grad_front.pdf": {"hash": pdf_hash},
            "https://example.com/grad_back.pdf": {"hash": pdf_hash},
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
        """Should handle mixed scenario: new + unchanged."""
        # Use HTML with 3 links — 2 are stored/unchanged, 1 is new
        mock_fetch.return_value = self.CHECK_FOR_UPDATES_HTML
        unchanged_content = b"unchanged"
        unchanged_hash = compute_hash(unchanged_content)
        mock_download.side_effect = [
            b"new content",       # grad_changes — not in stored
            unchanged_content,    # grad_front — unchanged
            unchanged_content,    # grad_back — unchanged
        ]
        mock_get_stored.return_value = {
            "https://example.com/grad_front.pdf": {"hash": unchanged_hash},
            "https://example.com/grad_back.pdf": {"hash": unchanged_hash},
        }

        result = check_for_updates()

        assert len(result) == 1
        assert result[0]["action"] == "new"
        assert mock_create_extraction.call_count == 1

    @patch("pipeline.monitor.fetch_page")
    @patch("pipeline.db.get_stored_pdf_links")
    def test_check_for_updates_no_links_found(
        self,
        mock_get_stored,
        mock_fetch,
    ) -> None:
        """Should return empty list when no PDF links found."""
        mock_fetch.return_value = "<div id='main'><section><p>No PDFs</p></section></div>"
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
        mock_fetch.return_value = self.CHECK_FOR_UPDATES_HTML
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
        mock_fetch.return_value = "<div id='main'><section></section></div>"

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
        mock_fetch.return_value = self.CHECK_FOR_UPDATES_HTML
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
        links = extract_pdf_links(REALISTIC_HTML)

        assert len(links) == 3
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
