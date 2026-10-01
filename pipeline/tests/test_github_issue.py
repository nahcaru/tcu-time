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


def _resp(status, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    r.text = text
    return r


def test_create_github_issue_success_one_issue_per_pdf(monkeypatch):
    sample_pdfs = [
        {
            "url": "https://example.com/tt_spring.pdf",
            "label": "2026年度前期時間割（確定版）",
            "action": "changed",
            "pdf_type": "timetable",
            "semester": "spring",
            "academic_year": 2026,
        },
        {
            "url": "https://example.com/advance.pdf",
            "label": "2026年度先行履修科目一覧",
            "action": "new",
            "pdf_type": "advance_enrollment",
            "semester": "both",
            "academic_year": 2026,
        },
    ]
    issues = iter(
        [
            {"number": 42, "html_url": "https://github.com/owner/repo/issues/42"},
            {"number": 43, "html_url": "https://github.com/owner/repo/issues/43"},
        ]
    )

    def fake_post(url, **kwargs):
        if url.endswith("/labels"):
            return _resp(201)
        return _resp(201, next(issues))

    with (
        patch("pipeline.services.github_issue_service.requests.post", side_effect=fake_post) as post,
        patch(
            "pipeline.services.github_issue_service.requests.get",
            return_value=_resp(200, []),
        ),
    ):
        result = create_github_issue_for_new_pdfs(
            sample_pdfs, github_token="ghp_test123", github_repo="owner/repo"
        )

    assert [i["number"] for i in result] == [42, 43]
    issue_calls = [c for c in post.call_args_list if c.args[0].endswith("/issues")]
    assert len(issue_calls) == 2
    first = issue_calls[0].kwargs["json"]
    assert first["title"] == "[TIME] 2026年度 前期 時間割を検出 (内容更新): 2026年度前期時間割（確定版）"
    assert first["labels"] == [
        "pdf-detected",
        "type:timetable",
        "semester:spring",
        "year:2026",
    ]
    assert "2026年度前期時間割（確定版）" in first["body"]
    assert "先行履修" not in first["body"]
    assert issue_calls[0].kwargs["headers"]["Authorization"] == "Bearer ghp_test123"


def test_create_github_issue_closes_superseded_with_link():
    pdf = {
        "url": "https://example.com/cl-1.pdf",
        "label": "授業時間表変更一覧",
        "action": "new",
        "pdf_type": "changelog",
        "semester": "fall",
        "academic_year": 2026,
    }
    new_issue = {"number": 17, "html_url": "https://github.com/owner/repo/issues/17"}

    def fake_post(url, **kwargs):
        if url.endswith("/labels"):
            return _resp(422)
        if url.endswith("/issues"):
            return _resp(201, new_issue)
        return _resp(201)

    with (
        patch("pipeline.services.github_issue_service.requests.post", side_effect=fake_post) as post,
        patch(
            "pipeline.services.github_issue_service.requests.get",
            return_value=_resp(200, [{"number": 16}, {"number": 17}, {"number": 9, "pull_request": {}}]),
        ) as get,
        patch(
            "pipeline.services.github_issue_service.requests.patch",
            return_value=_resp(200),
        ) as patch_req,
    ):
        create_github_issue_for_new_pdfs([pdf], github_token="t", github_repo="owner/repo")

    assert get.call_args.kwargs["params"]["labels"] == (
        "pdf-detected,type:changelog,semester:fall,year:2026"
    )
    # Only #16 is closed: not the new issue itself, not the PR
    assert patch_req.call_count == 1
    assert patch_req.call_args.args[0].endswith("/issues/16")
    assert patch_req.call_args.kwargs["json"] == {"state": "closed", "state_reason": "not_planned"}
    comment_calls = [c for c in post.call_args_list if c.args[0].endswith("/issues/16/comments")]
    assert len(comment_calls) == 1
    assert "#17" in comment_calls[0].kwargs["json"]["body"]


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
