"""Database repair script for extractions, pdf_links, and courses."""

from __future__ import annotations

import os
import re
from typing import Any

from pipeline.core.settings import Settings
from pipeline.extractors.timetable import infer_term_from_code
from pipeline.parsers.monitor_page import classify_pdf_link
from pipeline.repositories.common import get_client


def repair_database() -> None:
    Settings.SUPABASE_URL = os.environ["SUPABASE_URL"]
    Settings.SUPABASE_KEY = os.environ["SUPABASE_KEY"]
    client = get_client()

    print("=== Step 1: Repairing pdf_links ===")
    pdf_links_res = client.table("pdf_links").select("*").execute()
    for link in pdf_links_res.data:
        url = link["url"]
        old_label = link.get("label") or ""
        old_sem = link.get("semester")

        new_label = old_label
        if "/09/" in url and "後期" not in old_label:
            new_label = old_label.replace("授業時間表", "【後期】授業時間表")
            if "【後期】" not in new_label:
                new_label = f"〈総合理工学研究科〉【後期】{old_label}"
        elif ("/03/" in url or "/04/" in url) and "前期" not in old_label and "授業時間表" in old_label and "先行履修" not in old_label:
            new_label = old_label.replace("授業時間表", "【前期】授業時間表")

        meta = classify_pdf_link(new_label, url=url)
        new_sem = meta.semester.value if meta.semester else None

        if new_label != old_label or new_sem != old_sem:
            print(f"Updating pdf_link {url}: label='{new_label}', semester='{new_sem}'")
            client.table("pdf_links").update({
                "label": new_label,
                "semester": new_sem,
                "pdf_type": meta.pdf_type.value,
            }).eq("url", url).execute()

    print("\n=== Step 2: Repairing extractions ===")
    ext_res = client.table("extractions").select("*").execute()
    for ext in ext_res.data:
        eid = ext["id"]
        url = ext.get("pdf_url") or ""
        old_sem = ext.get("semester")
        raw = ext.get("raw_json") or {}
        courses = raw.get("courses", [])

        # Infer semester
        if "/09/" in url:
            correct_sem = "fall"
        elif "/03/" in url or "/04/" in url:
            correct_sem = "spring"
        else:
            correct_sem = old_sem

        raw_changed = False
        if raw.get("semester") != correct_sem:
            raw["semester"] = correct_sem
            raw_changed = True

        courses_repaired = 0
        for c in courses:
            current_term = c.get("term")
            code = c.get("code") or ""
            inferred_term = infer_term_from_code(code)
            if not current_term or (correct_sem == "fall" and "前" in current_term):
                new_term = inferred_term or ("後期前" if correct_sem == "fall" else "前期")
                if c.get("term") != new_term:
                    c["term"] = new_term
                    courses_repaired += 1
                    raw_changed = True

            if correct_sem and c.get("semester") != correct_sem:
                c["semester"] = correct_sem
                raw_changed = True

        update_payload: dict[str, Any] = {}
        if old_sem != correct_sem:
            update_payload["semester"] = correct_sem
        if raw_changed:
            update_payload["raw_json"] = raw

        if update_payload:
            print(f"Updating extraction {eid} (url={url.split('/')[-1]}): sem={old_sem}->{correct_sem}, courses repaired={courses_repaired}")
            client.table("extractions").update(update_payload).eq("id", eid).execute()

    print("\n=== Step 3: Repairing courses table ===")
    courses_res = client.table("courses").select("id, code, name, term, extraction_id").execute()
    repaired_courses = 0
    for c in courses_res.data:
        cid = c["id"]
        code = c.get("code") or ""
        current_term = (c.get("term") or "").strip()
        inferred = infer_term_from_code(code)

        needs_repair = False
        target_term = current_term
        if inferred:
            if not current_term:
                needs_repair = True
                target_term = inferred
            elif "前" in current_term and "後" in inferred:
                # Contradiction: code starts with smb... but term is 前期
                needs_repair = True
                target_term = inferred
            elif "後" in current_term and "前" in inferred:
                # Contradiction: code starts with sma... but term is 後期
                needs_repair = True
                target_term = inferred

        if needs_repair:
            print(f"Updating course {cid} ({code} {c['name']}): '{current_term}' -> '{target_term}'")
            client.table("courses").update({"term": target_term}).eq("id", cid).execute()
            repaired_courses += 1

    print(f"\nDone! Repaired {repaired_courses} courses in courses table.")


if __name__ == "__main__":
    repair_database()
