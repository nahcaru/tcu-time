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

ACTION_LABELS: dict[str, str] = {
    "new": "新規追加",
    "changed": "内容更新",
}


def create_github_issue_for_new_pdfs(
    new_pdfs: list[dict[str, Any]],
    *,
    github_token: str | None = None,
    github_repo: str | None = None,
) -> dict[str, Any] | None:
    """Create a GitHub Issue when new or changed PDFs are detected by the crawler.

    Opening an issue triggers GitHub's native email notification to maintainers.
    Gracefully skips when not running in a GitHub Actions environment or if token is absent.
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

    count = len(new_pdfs)
    title = f"[TIME] 新しいPDFが検出されました ({count}件)"

    rows: list[str] = []
    for pdf in new_pdfs:
        pdf_type = TYPE_LABELS.get(pdf.get("pdf_type", ""), pdf.get("pdf_type", "不明"))
        semester = SEMESTER_LABELS.get(pdf.get("semester", ""), pdf.get("semester", "不明"))
        action = ACTION_LABELS.get(pdf.get("action", ""), pdf.get("action", "検出"))
        label = pdf.get("label", "無題")
        url = pdf.get("url", "")
        rows.append(f"| {pdf_type} | {semester} | {action} | [{label}]({url}) |")

    table_rows = "\n".join(rows)

    body = f"""## 📄 新規・更新PDFの検出通知

クローラーにより新しいPDFが検出され、テキスト抽出が完了しました。
管理画面（Admin UI）にて抽出結果の確認と承認を行ってください。

### 検出されたPDF一覧

| 種別 | 学期 | アクション | ドキュメント |
| :--- | :--- | :--- | :--- |
{table_rows}

### 次のステップ
1. 管理画面（`/admin`）にアクセスします。
2. 該当する書類の差分・抽出データを確認します。
3. 問題がなければ「承認」を実行して本番データへ反映します。
4. 反映完了後、このIssueをクローズしてください。

---
*※ このIssueは GitHub Actions クローラーワークフローによって自動生成されました。*
"""

    api_url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": title,
        "body": body,
    }

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 201:
            data = resp.json()
            logger.info(
                "Created GitHub issue #%s for %d new PDF(s): %s",
                data.get("number"),
                count,
                data.get("html_url"),
            )
            return data
        else:
            logger.warning(
                "GitHub issue creation returned status %d: %s",
                resp.status_code,
                resp.text,
            )
            return None
    except requests.RequestException as e:
        logger.error("Failed to connect to GitHub API for issue notification: %s", e)
        return None
