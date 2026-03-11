"""End-to-end smoke tests for the pipeline flow.

Verifies: monitor → extractor → enricher using the real reference PDF but
with all external I/O (network, database) mocked.

The tests confirm that:
  1. Monitor can parse a realistic HTML page and detect a new PDF.
  2. Extractor can parse the reference PDF into structured courses.
  3. Enricher can process extracted courses with mocked syllabus HTML.
  4. The full pipeline (monitor → extractor → enricher) runs without error.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from ..monitor import (
    extract_pdf_links,
    check_for_updates,
    compute_hash as monitor_hash,
)
from ..extractor import (
    extract_courses_from_pdf,
    extract_tables_from_pdf,
)
from ..enricher import (
    enrich_courses,
    scrape_syllabus,
    SyllabusFields,
)
from ..models import ExtractedCourse, CourseMetadata

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_PDF_URL = "https://www.asc.tcu.ac.jp/wp-content/uploads/2025/03/grad_front.pdf"

REALISTIC_HTML = """\
<!DOCTYPE html>
<html>
<body>
<div class="entry-content">
<section>
<h2>【大学院】 総合理工学研究科（後期情報 11/27更新）</h2>
<details><summary>■前期■</summary>
<p><a href="{pdf_url}">〈総合理工学研究科〉全専攻 前期 授業時間表</a>（4/1更新）</p>
</details>
<details open=""><summary>■後期■</summary>
<p><a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/09/back.pdf">\
〈総合理工学研究科〉全専攻 後期 授業時間表</a>（9/15更新）</p>
</details>
<p><a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/04/changes.pdf">\
〈総合理工学研究科〉授業時間表変更一覧</a>（11/27更新）</p>
</section>
<section>
<h2>【学部】 理工学部</h2>
<a href="https://www.asc.tcu.ac.jp/wp-content/uploads/2025/03/undergrad.pdf">\
〈理工学部〉前期 授業時間表</a>
</section>
</div>
</body>
</html>
""".format(pdf_url=FAKE_PDF_URL)

FAKE_SYLLABUS_HTML = """\
<html><body>
<table class="syllabus_detail">
<tr><td class="label_kougi">分野系列</td><td class="kougi">■授業科目■</td></tr>
<tr><td class="label_kougi">単位数</td><td class="kougi">2</td></tr>
</table>
</body></html>
"""


@pytest.fixture
def reference_pdf_bytes(reference_pdf_path: Path) -> bytes:
    """Read the reference PDF as bytes (uses conftest fixture)."""
    assert reference_pdf_path.exists(), f"Reference PDF not found: {reference_pdf_path}"
    return reference_pdf_path.read_bytes()


# =============================================================================
# Stage 1: Monitor detects PDFs
# =============================================================================


class TestE2EMonitor:
    """Verify monitor correctly parses realistic page HTML."""

    def test_finds_grad_school_links_only(self) -> None:
        links = extract_pdf_links(REALISTIC_HTML)
        # Should find 3 grad school links, NOT the undergrad link
        assert len(links) == 3
        urls = [l.url for l in links]
        assert FAKE_PDF_URL in urls
        assert "undergrad.pdf" not in " ".join(urls)

    def test_link_labels_contain_grad_school(self) -> None:
        links = extract_pdf_links(REALISTIC_HTML)
        for link in links:
            assert "総合理工学研究科" in link.label

    @patch("pipeline.monitor.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.monitor.fetch_page")
    def test_monitor_queues_new_pdfs(
        self,
        mock_fetch: MagicMock,
        mock_download: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        """Monitor should queue all 3 PDFs when DB is empty (first run)."""
        mock_fetch.return_value = REALISTIC_HTML
        mock_download.return_value = b"fake-pdf-bytes"
        mock_db.get_stored_pdf_links.return_value = {}
        mock_db.upsert_pdf_link.return_value = {"id": "link-1"}
        mock_db.create_extraction.return_value = {"id": "ext-1"}

        result = check_for_updates("https://fake-url.com")

        assert len(result) == 3
        assert all(r["action"] == "new" for r in result)
        assert mock_db.upsert_pdf_link.call_count == 3
        assert mock_db.create_extraction.call_count == 3


# =============================================================================
# Stage 2: Extractor parses PDF
# =============================================================================


class TestE2EExtractor:
    """Verify extractor processes the real reference PDF."""

    def test_extracts_courses_from_real_pdf(
        self, reference_pdf_bytes: bytes
    ) -> None:
        """Full extraction from reference PDF produces valid courses."""
        courses = extract_courses_from_pdf(reference_pdf_bytes)

        # We know from previous work: ~199 courses
        assert len(courses) >= 150, f"Expected 150+ courses, got {len(courses)}"

        # Every course is a valid ExtractedCourse
        for course in courses:
            assert isinstance(course, ExtractedCourse)
            assert course.code.startswith("sm")
            assert len(course.instructors) >= 1
            # Intensive courses may have empty schedules (集中 with no day/period)
            # so we only check that most courses have schedules
        courses_with_schedules = [c for c in courses if c.schedules]
        assert len(courses_with_schedules) >= 100, (
            f"Expected 100+ courses with schedules, got {len(courses_with_schedules)}"
        )

    def test_no_duplicate_codes(self, reference_pdf_bytes: bytes) -> None:
        """Course codes should be unique after deduplication."""
        courses = extract_courses_from_pdf(reference_pdf_bytes)
        codes = [c.code for c in courses]
        assert len(codes) == len(set(codes)), "Duplicate course codes found"

    def test_has_both_regular_and_intensive(
        self, reference_pdf_bytes: bytes
    ) -> None:
        """Should contain both regular (day+period) and intensive courses."""
        courses = extract_courses_from_pdf(reference_pdf_bytes)

        regular = [
            c
            for c in courses
            if any(s.term in ("前期前", "前期後", "前期") for s in c.schedules)
            and any(s.day != "" for s in c.schedules)
        ]
        intensive = [
            c
            for c in courses
            if any("集中" in s.term for s in c.schedules)
        ]

        assert len(regular) > 0, "No regular courses found"
        assert len(intensive) > 0, "No intensive courses found"


# =============================================================================
# Stage 3: Enricher processes courses
# =============================================================================


class TestE2EEnricher:
    """Verify enricher works with mocked syllabus pages."""

    @patch("pipeline.enricher.time.sleep")
    @patch("pipeline.enricher.fetch_syllabus_page")
    @patch("pipeline.enricher.db")
    def test_enricher_processes_courses(
        self,
        mock_db: MagicMock,
        mock_fetch: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        """Enricher should process courses and call db.upsert_metadata."""
        mock_fetch.return_value = FAKE_SYLLABUS_HTML
        mock_db.upsert_metadata.return_value = {"id": "meta-1"}

        # Simulate 2 courses from extractor output
        courses = [
            {
                "id": "course-id-1",
                "code": "smab020161",
                "name": "Test Course 1",
                "targets": [],
            },
            {
                "id": "course-id-2",
                "code": "smcd030201",
                "name": "Test Course 2",
                "targets": [],
            },
        ]

        success, failure = enrich_courses(courses, academic_year=2025)

        assert success == 2
        assert failure == 0
        assert mock_db.upsert_metadata.call_count == 2

    @patch("pipeline.enricher.fetch_syllabus_page")
    def test_scrape_syllabus_returns_metadata(
        self,
        mock_fetch: MagicMock,
    ) -> None:
        """scrape_syllabus should return CourseMetadata from HTML."""
        mock_fetch.return_value = FAKE_SYLLABUS_HTML

        result = scrape_syllabus(2025, "smab020161")

        assert result is not None
        assert isinstance(result, CourseMetadata)
        assert result.category == "授業科目"
        assert result.credits == 2.0
        assert result.curriculum_code == "default"


# =============================================================================
# Full pipeline flow
# =============================================================================


class TestE2EFullPipeline:
    """Simulate the full pipeline: monitor → extractor → enricher."""

    @patch("pipeline.enricher.time.sleep")
    @patch("pipeline.enricher.fetch_syllabus_page")
    @patch("pipeline.enricher.db")
    @patch("pipeline.monitor.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.monitor.fetch_page")
    def test_full_pipeline_flow(
        self,
        mock_fetch_page: MagicMock,
        mock_download_pdf: MagicMock,
        mock_monitor_db: MagicMock,
        mock_enricher_db: MagicMock,
        mock_fetch_syllabus: MagicMock,
        mock_sleep: MagicMock,
        reference_pdf_bytes: bytes,
    ) -> None:
        """Full flow: monitor finds PDF → extractor parses it → enricher enriches.

        This test wires all three stages together using real PDF parsing but
        mocked network and DB calls.
        """
        # --- Stage 1: Monitor ---
        mock_fetch_page.return_value = REALISTIC_HTML
        mock_download_pdf.return_value = reference_pdf_bytes
        mock_monitor_db.get_stored_pdf_links.return_value = {}
        mock_monitor_db.upsert_pdf_link.return_value = {"id": "link-1"}
        mock_monitor_db.create_extraction.return_value = {"id": "ext-1"}

        queued = check_for_updates("https://fake-url.com")
        assert len(queued) >= 1  # At least the front semester PDF

        # --- Stage 2: Extractor ---
        # Use the real PDF bytes that the monitor would have downloaded
        courses = extract_courses_from_pdf(reference_pdf_bytes)
        assert len(courses) >= 150

        # --- Stage 3: Enricher ---
        # Simulate DB output from extractor: courses with IDs
        mock_fetch_syllabus.return_value = FAKE_SYLLABUS_HTML
        mock_enricher_db.upsert_metadata.return_value = {"id": "meta-1"}

        course_rows = [
            {"id": f"course-{i}", "code": c.code, "name": c.name, "targets": []}
            for i, c in enumerate(courses[:3])  # Only enrich first 3 for speed
        ]

        success, failure = enrich_courses(course_rows, academic_year=2025)

        assert success == 3
        assert failure == 0
        assert mock_enricher_db.upsert_metadata.call_count == 3

    @patch("pipeline.monitor.db")
    @patch("pipeline.monitor.download_pdf")
    @patch("pipeline.monitor.fetch_page")
    def test_no_change_skips_pipeline(
        self,
        mock_fetch_page: MagicMock,
        mock_download_pdf: MagicMock,
        mock_db: MagicMock,
        reference_pdf_bytes: bytes,
    ) -> None:
        """When PDFs haven't changed, nothing should be queued."""
        pdf_hash = hashlib.sha256(reference_pdf_bytes).hexdigest()

        mock_fetch_page.return_value = REALISTIC_HTML
        mock_download_pdf.return_value = reference_pdf_bytes

        # All 3 links already stored with current hashes
        mock_db.get_stored_pdf_links.return_value = {
            FAKE_PDF_URL: {"hash": pdf_hash},
            "https://www.asc.tcu.ac.jp/wp-content/uploads/2025/09/back.pdf": {"hash": pdf_hash},
            "https://www.asc.tcu.ac.jp/wp-content/uploads/2025/04/changes.pdf": {"hash": pdf_hash},
        }

        queued = check_for_updates("https://fake-url.com")
        assert len(queued) == 0
        mock_db.create_extraction.assert_not_called()
