from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

TYPE_LABELS: dict[str, str] = {
    "timetable": "時間割",
    "changelog": "変更一覧",
    "advance_enrollment": "先行履修",
}

SEMESTER_LABELS: dict[str, str] = {
    "spring": "前期",
    "fall": "後期",
    "both": "通年 / 両学期",
}

BASE_LABEL = "pdf-detected"

ACTION_LABELS: dict[str, str] = {
    "new": "新規追加",
    "changed": "内容更新",
}


def _identity_labels(pdf: dict[str, Any]) -> list[str]:
    """Labels identifying "the same kind of document": (academic_year, pdf_type, semester).

    Mirrors the document identity used by the admin ExtractionList "latest only" filter.
    """
    labels = [
        f"type:{pdf.get('pdf_type') or 'unknown'}",
        f"semester:{pdf.get('semester') or 'both'}",
    ]
    if pdf.get("academic_year"):
        labels.append(f"year:{pdf['academic_year']}")
    return labels


def _build_title(pdf: dict[str, Any]) -> str:
    pdf_type = TYPE_LABELS.get(pdf.get("pdf_type", ""), pdf.get("pdf_type", "不明"))
    semester = SEMESTER_LABELS.get(pdf.get("semester", ""), pdf.get("semester", "不明"))
    action = ACTION_LABELS.get(pdf.get("action", ""), pdf.get("action", "検出"))
    year = f"{pdf['academic_year']}年度 " if pdf.get("academic_year") else ""
    return f"[TIME] {year}{semester} {pdf_type}を検出 ({action}): {pdf.get('label', '無題')}"


def _build_body(pdf: dict[str, Any]) -> str:
    pdf_type = TYPE_LABELS.get(pdf.get("pdf_type", ""), pdf.get("pdf_type", "不明"))
    semester = SEMESTER_LABELS.get(pdf.get("semester", ""), pdf.get("semester", "不明"))
    action = ACTION_LABELS.get(pdf.get("action", ""), pdf.get("action", "検出"))
    label = pdf.get("label", "無題")
    url = pdf.get("url", "")

    return f"""## 📄 新規・更新PDFの検出通知

クローラーにより新しいPDFが検出され、テキスト抽出が完了しました。
管理画面（Admin UI）にて抽出結果の確認と承認を行ってください。

### 検出されたPDF

| 種別 | 学期 | アクション | ドキュメント |
| :--- | :--- | :--- | :--- |
| {pdf_type} | {semester} | {action} | [{label}]({url}) |

### 次のステップ
1. 管理画面（`/admin`）にアクセスします。
2. 該当する書類の差分・抽出データを確認します。
3. 問題がなければ「承認」を実行して本番データへ反映します。
4. 反映完了後、このIssueをクローズしてください。

同種のPDFが再度検出された場合、このIssueは新しいIssueへのリンクを添えて自動的にクローズされます。

---
*※ このIssueは GitHub Actions クローラーワークフローによって自動生成されました。*
"""


def _ensure_labels(api_url: str, headers: dict[str, str], labels: list[str]) -> None:
    for name in labels:
        try:
            resp = requests.post(
                f"{api_url}/labels", json={"name": name}, headers=headers, timeout=15
            )
            # 422 = label already exists
            if resp.status_code not in (201, 422):
                logger.warning("Label creation for %s returned %d", name, resp.status_code)
        except requests.RequestException:
            logger.warning("Failed to ensure label %s", name, exc_info=True)


def _close_superseded_issues(
    api_url: str,
    headers: dict[str, str],
    *,
    labels: list[str],
    new_issue: dict[str, Any],
) -> None:
    """Close open issues of the same document kind, linking to the new issue."""
    resp = requests.get(
        f"{api_url}/issues",
        params={"state": "open", "labels": ",".join([BASE_LABEL, *labels]), "per_page": 100},
        headers=headers,
        timeout=15,
    )
    if resp.status_code != 200:
        logger.warning("Listing superseded issues returned %d: %s", resp.status_code, resp.text)
        return

    for old in resp.json():
        # The issues endpoint also returns pull requests; skip them and the new issue itself.
        if "pull_request" in old or old.get("number") == new_issue.get("number"):
            continue
        number = old["number"]
        comment = (
            f"同種のPDFの新しい版が検出されたため、このIssueをクローズします。"
            f"\n\n最新: #{new_issue.get('number')} ({new_issue.get('html_url')})"
        )
        requests.post(
            f"{api_url}/issues/{number}/comments",
            json={"body": comment},
            headers=headers,
            timeout=15,
        )
        close = requests.patch(
            f"{api_url}/issues/{number}",
            json={"state": "closed", "state_reason": "not_planned"},
            headers=headers,
            timeout=15,
        )
        if close.status_code == 200:
            logger.info("Closed superseded issue #%s", number)
        else:
            logger.warning("Closing issue #%s returned %d: %s", number, close.status_code, close.text)


def create_github_issue_for_new_pdfs(
    new_pdfs: list[dict[str, Any]],
    *,
    github_token: str | None = None,
    github_repo: str | None = None,
) -> list[dict[str, Any]] | None:
    """Create one GitHub Issue per new or changed PDF detected by the crawler.

    Issues are labelled by document kind (type / semester / academic year); open issues of
    the same kind are closed with a link to the new one so only the latest stays open.
    Opening an issue triggers GitHub's native email notification to maintainers.
    Gracefully skips when not running in a GitHub Actions environment or if token is absent.

    Returns the created issues, or None if nothing was created.
    """
    if not new_pdfs:
        return None

    token = github_token or os.environ.get("GITHUB_TOKEN")
    repo = github_repo or os.environ.get("GITHUB_REPOSITORY")

    if not token or not repo:
        logger.info(
            "GITHUB_TOKEN or GITHUB_REPOSITORY not set; skipping GitHub issue notification."
        )
        return None

    api_url = f"https://api.github.com/repos/{repo}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    created: list[dict[str, Any]] = []
    for pdf in new_pdfs:
        labels = _identity_labels(pdf)
        try:
            _ensure_labels(api_url, headers, [BASE_LABEL, *labels])
            resp = requests.post(
                f"{api_url}/issues",
                json={
                    "title": _build_title(pdf),
                    "body": _build_body(pdf),
                    "labels": [BASE_LABEL, *labels],
                },
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 201:
                logger.warning(
                    "GitHub issue creation returned status %d: %s",
                    resp.status_code,
                    resp.text,
                )
                continue
            data = resp.json()
            logger.info("Created GitHub issue #%s: %s", data.get("number"), data.get("html_url"))
            created.append(data)
            _close_superseded_issues(api_url, headers, labels=labels, new_issue=data)
        except requests.RequestException as e:
            logger.error("Failed to connect to GitHub API for issue notification: %s", e)

    return created or None
