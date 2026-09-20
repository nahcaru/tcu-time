"""Repair fullwidth/halfwidth inconsistencies and whitespace variations in Supabase.

Normalizes:
1. courses table:
   - instructors: Fullwidth space to single halfwidth space, strip whitespace
   - name: Fullwidth alphanumeric/symbols to halfwidth, parentheses to halfwidth
   - room: Parentheses to halfwidth, alphanumeric to halfwidth
   - notes: Parentheses to halfwidth
2. course_targets table:
   - note: Tildes (～, 〜) to ~, parentheses to halfwidth
   - target_name: Text normalization
3. extractions table:
   - raw_json (courses, changes, names): Normalize extracted content so that future
     re-approvals or audits don't re-introduce unnormalized data.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# Ensure pipeline and project root are in sys.path
PIPELINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TIME_DIR = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
if TIME_DIR not in sys.path:
    sys.path.insert(0, TIME_DIR)
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

# Load .env
env_path = os.path.join(PIPELINE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("\"'")

from pipeline.core.normalize import (
    normalize_course_dict,
    normalize_course_name,
    normalize_instructor_name,
    normalize_note,
    normalize_room,
    normalize_target_note,
    normalize_text,
)
from pipeline.core.settings import Settings

Settings.SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
Settings.SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

from pipeline.repositories.common import get_client


def repair_courses(client: Any, dry_run: bool) -> int:
    print("\n--- 1. Repairing courses table ---")
    res = client.table("courses").select("id, code, academic_year, name, instructors, room, notes").execute()
    courses = res.data or []
    print(f"Total courses fetched: {len(courses)}")

    update_count = 0
    for c in courses:
        cid = c["id"]
        code = c["code"]
        year = c["academic_year"]

        orig_name = c.get("name") or ""
        orig_inst = c.get("instructors") or []
        orig_room = c.get("room") or ""
        orig_notes = c.get("notes") or ""

        norm_name = normalize_course_name(orig_name)
        norm_inst = [normalize_instructor_name(i) for i in orig_inst if normalize_instructor_name(i)] or ["未定"]
        norm_room = normalize_room(orig_room)
        norm_notes = normalize_note(orig_notes)

        changes: dict[str, Any] = {}
        if orig_name != norm_name:
            changes["name"] = norm_name
            print(f"  [{code} {year}] name: {repr(orig_name)} -> {repr(norm_name)}")

        if orig_inst != norm_inst:
            changes["instructors"] = norm_inst
            print(f"  [{code} {year}] instructors: {orig_inst} -> {norm_inst}")

        if orig_room != norm_room:
            changes["room"] = norm_room
            print(f"  [{code} {year}] room: {repr(orig_room)} -> {repr(norm_room)}")

        if orig_notes != norm_notes:
            changes["notes"] = norm_notes
            print(f"  [{code} {year}] notes: {repr(orig_notes)} -> {repr(norm_notes)}")

        if changes:
            update_count += 1
            if not dry_run:
                client.table("courses").update(changes).eq("id", cid).execute()

    print(f"Courses modified: {update_count} / {len(courses)}")
    return update_count


def repair_course_targets(client: Any, dry_run: bool) -> int:
    print("\n--- 2. Repairing course_targets table ---")
    res = client.table("course_targets").select("course_id, target_code, target_name, note").execute()
    targets = res.data or []
    print(f"Total course_targets fetched: {len(targets)}")

    update_count = 0
    for t in targets:
        cid = t["course_id"]
        tcode = t["target_code"]

        orig_name = t.get("target_name") or ""
        orig_note = t.get("note") or ""

        norm_name = normalize_text(orig_name)
        norm_note = normalize_target_note(orig_note)

        changes: dict[str, Any] = {}
        if orig_name != norm_name:
            changes["target_name"] = norm_name
            print(f"  [target {cid}:{tcode}] target_name: {repr(orig_name)} -> {repr(norm_name)}")

        if orig_note != norm_note:
            changes["note"] = norm_note
            print(f"  [target {cid}:{tcode}] note: {repr(orig_note)} -> {repr(norm_note)}")

        if changes:
            update_count += 1
            if not dry_run:
                (
                    client.table("course_targets")
                    .update(changes)
                    .eq("course_id", cid)
                    .eq("target_code", tcode)
                    .execute()
                )

    print(f"course_targets modified: {update_count} / {len(targets)}")
    return update_count


def repair_extractions(client: Any, dry_run: bool) -> int:
    print("\n--- 3. Repairing extractions raw_json ---")
    res = client.table("extractions").select("id, pdf_url, pdf_type, raw_json").execute()
    exts = res.data or []
    print(f"Total extractions fetched: {len(exts)}")

    update_count = 0
    for ext in exts:
        eid = ext["id"]
        raw = ext.get("raw_json")
        if not isinstance(raw, dict):
            continue

        modified = False
        new_raw = dict(raw)

        # 3a. courses list
        if "courses" in new_raw and isinstance(new_raw["courses"], list):
            new_courses = []
            courses_changed = 0
            for c in new_raw["courses"]:
                if isinstance(c, dict):
                    norm_c = normalize_course_dict(c)
                    if norm_c != c:
                        courses_changed += 1
                    new_courses.append(norm_c)
                else:
                    new_courses.append(c)
            if courses_changed > 0:
                print(f"  [Extraction {eid[:8]}] Normalized {courses_changed} courses in raw_json")
                new_raw["courses"] = new_courses
                modified = True

        # 3b. changes list (changelogs)
        if "changes" in new_raw and isinstance(new_raw["changes"], list):
            new_changes = []
            changes_changed = 0
            for ch in new_raw["changes"]:
                if isinstance(ch, dict):
                    norm_ch = dict(ch)
                    if "course_name" in norm_ch and norm_ch["course_name"]:
                        norm_ch["course_name"] = normalize_course_name(norm_ch["course_name"])
                    if "instructors" in norm_ch and isinstance(norm_ch["instructors"], list):
                        norm_ch["instructors"] = [
                            normalize_instructor_name(i) for i in norm_ch["instructors"] if normalize_instructor_name(i)
                        ]
                    if norm_ch != ch:
                        changes_changed += 1
                    new_changes.append(norm_ch)
                else:
                    new_changes.append(ch)
            if changes_changed > 0:
                print(f"  [Extraction {eid[:8]}] Normalized {changes_changed} changes in raw_json")
                new_raw["changes"] = new_changes
                modified = True

        # 3c. names list (advance enrollment)
        if "names" in new_raw and isinstance(new_raw["names"], list):
            new_names = [normalize_course_name(n) for n in new_raw["names"] if n]
            if new_names != new_raw["names"]:
                print(f"  [Extraction {eid[:8]}] Normalized advance enrollment names in raw_json")
                new_raw["names"] = new_names
                modified = True

        if modified:
            update_count += 1
            if not dry_run:
                client.table("extractions").update({"raw_json": new_raw}).eq("id", eid).execute()

    print(f"Extractions modified: {update_count} / {len(exts)}")
    return update_count


def main():
    parser = argparse.ArgumentParser(description="Repair fullwidth/halfwidth inconsistencies in Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without modifying database")
    args = parser.parse_args()

    client = get_client()
    dry_run = args.dry_run

    print(f"=== Starting Data Normalization Repair (dry_run={dry_run}) ===")
    c_count = repair_courses(client, dry_run)
    t_count = repair_course_targets(client, dry_run)
    e_count = repair_extractions(client, dry_run)

    print("\n=== Repair Summary ===")
    print(f"  Courses modified: {c_count}")
    print(f"  Targets modified: {t_count}")
    print(f"  Extractions modified: {e_count}")
    if dry_run:
        print("\n[DRY RUN] No changes were written to the database. Run without --dry-run to apply.")
    else:
        print("\n[SUCCESS] All modifications successfully written to the database.")


if __name__ == "__main__":
    main()
