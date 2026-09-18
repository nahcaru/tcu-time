from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from pipeline.services.extraction_service import run_pipeline_workflow
from pipeline.services.github_issue_service import create_github_issue_for_new_pdfs


def test_create_github_issue_empty_pdfs():
    result = create_github_issue_for_new_pdfs([], github_token="fake", github_repo="owner/repo")
    assert result is None


def test_create_github_issue_missing_env(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    sample_pdfs = [
        {
            "url": "https://example.com/timetable.pdf",
            "label": "2026年度前期時間割",
            "action": "new",
            "pdf_type": "timetable",
            "semester": "spring",
        }
    ]
    result = create_github_issue_for_new_pdfs(sample_pdfs)
    assert result is None


def test_create_github_issue_success(monkeypatch):
    sample_pdfs = [
        {
            "url": "https://example.com/tt_spring.pdf",
            "label": "2026年度前期時間割（確定版）",
            "action": "changed",
            "pdf_type": "timetable",
            "semester": "spring",
        },
        {
            "url": "https://example.com/advance.pdf",
            "label": "2026年度先行履修科目一覧",
            "action": "new",
            "pdf_type": "advance_enrollment",
            "semester": "both",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "number": 42,
        "html_url": "https://github.com/owner/repo/issues/42",
    }

    with patch("pipeline.services.github_issue_service.requests.post", return_value=mock_resp) as mock_post:
        result = create_github_issue_for_new_pdfs(
            sample_pdfs,
            github_token="ghp_test123",
            github_repo="owner/repo",
        )

        assert result is not None
        assert result["number"] == 42
        assert result["html_url"] == "https://github.com/owner/repo/issues/42"

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.github.com/repos/owner/repo/issues"
        assert kwargs["headers"]["Authorization"] == "Bearer ghp_test123"
        payload = kwargs["json"]
        assert "[TIME] 新しいPDFが検出されました (2件)" in payload["title"]
        assert "2026年度前期時間割（確定版）" in payload["body"]
        assert "先行履修" in payload["body"]


def test_create_github_issue_api_error():
    sample_pdfs = [
        {
            "url": "https://example.com/tt.pdf",
            "label": "時間割",
            "action": "new",
            "pdf_type": "timetable",
            "semester": "spring",
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "Resource not accessible by integration"

    with patch("pipeline.services.github_issue_service.requests.post", return_value=mock_resp):
        result = create_github_issue_for_new_pdfs(
            sample_pdfs,
            github_token="token",
            github_repo="owner/repo",
        )
        assert result is None


def test_create_github_issue_network_exception():
    sample_pdfs = [
        {
            "url": "https://example.com/tt.pdf",
            "label": "時間割",
            "action": "new",
            "pdf_type": "timetable",
            "semester": "spring",
        }
    ]

    with patch(
        "pipeline.services.github_issue_service.requests.post",
        side_effect=requests.RequestException("Connection timed out"),
    ):
        result = create_github_issue_for_new_pdfs(
            sample_pdfs,
            github_token="token",
            github_repo="owner/repo",
        )
        assert result is None


def test_run_pipeline_workflow_triggers_github_notification():
    mock_check = MagicMock(
        return_value=[
            {
                "url": "https://example.com/tt.pdf",
                "label": "2026前期時間割",
                "action": "new",
                "pdf_type": "timetable",
                "semester": "spring",
            }
        ]
    )
    mock_download = MagicMock(return_value=b"%PDF-test")
    mock_hash = MagicMock(return_value="hash123")
    mock_pending = MagicMock(
        return_value=[
            {"id": "ext-1", "pdf_url": "https://example.com/tt.pdf", "pdf_hash": "hash123"}
        ]
    )
    mock_process = MagicMock()
    mock_notify = MagicMock()

    run_pipeline_workflow(
        check_for_updates=mock_check,
        download_pdf=mock_download,
        compute_hash=mock_hash,
        get_pending_extractions=mock_pending,
        process_extraction=mock_process,
        notify_new_pdfs=mock_notify,
    )

    mock_notify.assert_called_once()
    passed_pdfs = mock_notify.call_args[0][0]
    assert len(passed_pdfs) == 1
    assert passed_pdfs[0]["url"] == "https://example.com/tt.pdf"
