"""CLI entry point for the syllabus search scraper.

Usage::

    # Dry-run: scrape and log results without DB writes
    python -m pipeline.scrape_syllabus --dry-run

    # Production: scrape and upsert into connected Supabase instance
    python -m pipeline.scrape_syllabus

    # Override academic year
    python -m pipeline.scrape_syllabus --year 2026

The script scrapes fall-semester course data from the TCU syllabus search
site and upserts it directly into the courses, schedules, course_targets,
and course_metadata tables. Intended for use with a Supabase preview branch.
"""

from __future__ import annotations

import argparse
import json
import logging

from pipeline.core.academic_year import current_academic_year
from pipeline.core.settings import Settings
from pipeline.services.syllabus_scraper_service import (
    CURRICULA,
    KAIKO_CODES,
    persist_courses,
    scrape_all_courses,
)

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape fall-semester courses from TCU syllabus search site.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Academic year (default: auto-detect).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and log results without writing to the database.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=Settings.SCRAPE_DELAY_SEC,
        help="Delay between HTTP requests in seconds (default: %(default)s).",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = _parse_args()
    year = args.year or current_academic_year()

    if not args.dry_run:
        Settings.validate(required=("SUPABASE_URL", "SUPABASE_KEY"))

    logger.info("=" * 60)
    logger.info("TCU Syllabus Search Scraper")
    logger.info("=" * 60)
    logger.info("Academic year: %d", year)
    logger.info("Curricula: %d", len(CURRICULA))
    logger.info("Term codes: %s", ", ".join(KAIKO_CODES.values()))
    logger.info("Dry run: %s", args.dry_run)
    logger.info("=" * 60)

    courses = scrape_all_courses(
        year,
        delay=args.delay,
        dry_run=args.dry_run,
    )

    if not courses:
        logger.info("No courses found — nothing to do.")
        return

    # Log summary
    logger.info("-" * 60)
    logger.info("Summary: %d unique courses scraped", len(courses))
    for c in courses:
        targets_str = ", ".join(
            f"{t['target_code']}:{t['target_name']}" for t in c.targets
        )
        schedules_str = ", ".join(
            f"{s['day']}{s['period']}" for s in c.schedules
        )
        logger.info(
            "  %s | %s | %s | [%s] | targets=[%s]",
            c.code,
            c.term,
            c.name,
            schedules_str,
            targets_str,
        )

    if args.dry_run:
        # Dump as JSON for inspection
        dump = [
            {
                "code": c.code,
                "name": c.name,
                "instructors": c.instructors,
                "term": c.term,
                "schedules": c.schedules,
                "targets": c.targets,
                "credits": c.credits,
                "category": c.category,
            }
            for c in courses
        ]
        logger.info("Dry-run JSON output:\n%s", json.dumps(dump, ensure_ascii=False, indent=2))
        logger.info("Dry run complete — no data written to database.")
        return

    # Persist to DB
    logger.info("-" * 60)
    logger.info("Upserting %d courses to database ...", len(courses))
    courses_count, meta_count = persist_courses(courses, year)
    logger.info(
        "Done: %d courses upserted, %d metadata records upserted.",
        courses_count,
        meta_count,
    )


if __name__ == "__main__":
    main()
