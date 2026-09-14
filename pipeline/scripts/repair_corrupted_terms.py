"""Repair script strictly for 2026 academic year Fall semester timetable courses.

Updates courses where:
  academic_year == 2026
  term == '後集中'
  Course has regular schedule slots (day in 月-金, period 1-5)

Updates term from '後集中' -> '後期'.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, ".")

from pipeline.models import VALID_DAYS
from pipeline.repositories.common import get_client


def repair_2026_fall_terms() -> int:
    client = get_client()

    # 1. Fetch 2026 courses currently marked as '後集中'
    courses_res = (
        client.table("courses")
        .select("id, code, name, term, academic_year")
        .eq("academic_year", 2026)
        .eq("term", "後集中")
        .execute()
    )

    courses = courses_res.data or []
    if not courses:
        print("No 2026 courses found with term == '後集中'.")
        return 0

    course_ids = [c["id"] for c in courses]
    print(f"Found {len(courses)} courses in 2026 with term == '後集中'.")

    # 2. Query schedules for these courses
    sched_res = (
        client.table("schedules")
        .select("course_id, day, period")
        .in_("course_id", course_ids)
        .execute()
    )

    schedules = sched_res.data or []
    # Identify course IDs that have regular weekly schedules
    courses_with_regular_sched = set()
    for s in schedules:
        day = s.get("day")
        period = s.get("period")
        if day in VALID_DAYS and period is not None and 1 <= period <= 5:
            courses_with_regular_sched.add(s["course_id"])

    # 3. Update only the courses that have regular schedules
    repaired_count = 0
    for c in courses:
        cid = c["id"]
        if cid in courses_with_regular_sched:
            code = c.get("code")
            name = c.get("name")
            print(f"Repairing course {code} ({name}): '後集中' -> '後期'")
            client.table("courses").update({"term": "後期"}).eq("id", cid).execute()
            repaired_count += 1
        else:
            print(f"Skipping true intensive course (no weekly schedule): {c.get('code')} ({c.get('name')})")

    print(f"\n[Done] Repaired {repaired_count} courses in 2026 Fall timetable.")
    return repaired_count


if __name__ == "__main__":
    repair_2026_fall_terms()
