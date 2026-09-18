"""Repair data anomalies in approved 2026 courses in Supabase.

1. Fix class_section="1" mistakenly set on 8 smbb courses -> reset to ""
2. Fix truncated note in course_targets for smbz110011 -> set to "～24計算科学特論"
3. Update raw_json in extractions table to keep audit history consistent
"""

import argparse
import json
import os
import sys

# Ensure pipeline root is in sys.path
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

from pipeline.core.settings import Settings
Settings.SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
Settings.SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

from pipeline.repositories.common import get_client


CLASS_SECTION_FIX_CODES = [
    "smbb010011",
    "smbb020011",
    "smbb020111",
    "smbb030021",
    "smbb030131",
    "smbb040021",
    "smbb050131",
    "smbb080011",
]

TARGET_NOTE_FIX_CODE = "smbz110011"
TARGET_NOTE_OLD = "～24計算科学特"
TARGET_NOTE_NEW = "～24計算科学特論"


def main():
    parser = argparse.ArgumentParser(description="Repair approved 2026 courses")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without modifying the database")
    args = parser.parse_args()

    client = get_client()
    dry_run = args.dry_run

    print(f"=== Starting 2026 Data Repair (dry_run={dry_run}) ===")

    # 1. Fix class_section
    print("\n--- 1. Fixing class_section for 8 courses ---")
    res_courses = (
        client.table("courses")
        .select("id, code, name, academic_year, class_section")
        .in_("code", CLASS_SECTION_FIX_CODES)
        .eq("academic_year", 2026)
        .execute()
    )
    courses_to_fix = res_courses.data or []
    print(f"Found {len(courses_to_fix)} courses in DB:")
    for c in courses_to_fix:
        print(f"  {c['code']} {c['name']} (id={c['id']}): class_section '{c['class_section']}' -> ''")

    if not dry_run:
        for c in courses_to_fix:
            client.table("courses").update({"class_section": ""}).eq("id", c["id"]).execute()
        print("  -> Updated courses table successfully.")

    # 2. Fix course_targets note
    print(f"\n--- 2. Fixing course_targets note for {TARGET_NOTE_FIX_CODE} ---")
    course_target_parent = (
        client.table("courses")
        .select("id, code, name, academic_year")
        .eq("code", TARGET_NOTE_FIX_CODE)
        .eq("academic_year", 2026)
        .single()
        .execute()
    )
    parent_id = course_target_parent.data["id"]
    targets_res = (
        client.table("course_targets")
        .select("*")
        .eq("course_id", parent_id)
        .eq("target_code", "11")
        .execute()
    )
    targets = targets_res.data or []
    print(f"Found target student record: {targets}")
    for t in targets:
        print(f"  note: '{t['note']}' -> '{TARGET_NOTE_NEW}'")

    if not dry_run:
        (
            client.table("course_targets")
            .update({"note": TARGET_NOTE_NEW})
            .eq("course_id", parent_id)
            .eq("target_code", "11")
            .execute()
        )
        print("  -> Updated course_targets table successfully.")

    # 3. Update raw_json in extractions table
    extraction_id = "8711ac3c-c91a-4bbe-8db8-2fa9213da88f"
    print(f"\n--- 3. Updating raw_json in extractions ({extraction_id}) ---")
    ext_res = client.table("extractions").select("id, raw_json").eq("id", extraction_id).execute()
    if ext_res.data:
        raw_json = ext_res.data[0]["raw_json"]
        courses_in_raw = raw_json.get("courses", [])
        modified_count = 0
        for c in courses_in_raw:
            if c.get("code") in CLASS_SECTION_FIX_CODES and c.get("class_section") == "1":
                c["class_section"] = ""
                modified_count += 1
            if c.get("code") == TARGET_NOTE_FIX_CODE:
                for t in c.get("targets", []):
                    if t.get("target_code") == "11" and t.get("note") == TARGET_NOTE_OLD:
                        t["note"] = TARGET_NOTE_NEW
                        modified_count += 1
                if c.get("target_raw", "").endswith("～24計算科学特"):
                    c["target_raw"] = c["target_raw"] + "論]"
                    modified_count += 1
        print(f"  Modified {modified_count} fields in raw_json")

        if not dry_run:
            client.table("extractions").update({"raw_json": raw_json}).eq("id", extraction_id).execute()
            print("  -> Updated extractions.raw_json successfully.")

    print("\n=== Repair Completed Successfully ===")


if __name__ == "__main__":
    main()
