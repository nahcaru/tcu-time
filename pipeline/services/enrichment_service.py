from __future__ import annotations

import logging

from pipeline.config import Config
from pipeline.models import CourseMetadata

logger = logging.getLogger(__name__)

DEFAULT_CURRICULUM_CODE = "default"


def build_syllabus_url(year: int, course_code: str) -> str:
    base = Config.SYLLABUS_BASE_URL.rstrip("/")
    params = (
        f"value(risyunen)={year}"
        f"&value(semekikn)=1"
        f"&value(kougicd)={course_code}"
    )
    return f"{base}/slbssbdr.do?{params}"


def scrape_syllabus(
    year: int,
    course_code: str,
    *,
    fetch_syllabus_page,
    build_syllabus_url,
    parse_syllabus_html,
) -> CourseMetadata | None:
    url = build_syllabus_url(year, course_code)
    html = fetch_syllabus_page(url)
    if html is None:
        return None

    fields = parse_syllabus_html(html)
    return CourseMetadata(
        curriculum_code=DEFAULT_CURRICULUM_CODE,
        category=fields.category,
        credits=fields.credits,
    )


def enrich_courses(
    courses: list[dict],
    academic_year: int,
    *,
    scrape_syllabus,
    sleep,
    upsert_metadata,
) -> tuple[int, int]:
    if not courses:
        return 0, 0

    success = 0
    failure = 0

    for i, course in enumerate(courses):
        course_id: str = course["id"]
        course_code: str = course["code"]
        course_name: str = course.get("name", course_code)

        logger.info(
            "[%d/%d] Enriching %s (%s)",
            i + 1,
            len(courses),
            course_name,
            course_code,
        )

        if i > 0:
            sleep(Config.SCRAPE_DELAY_SEC)

        meta = scrape_syllabus(academic_year, course_code)
        if meta is None:
            logger.warning("Failed to scrape syllabus for %s", course_code)
            failure += 1
            continue

        try:
            upsert_metadata(
                course_id=course_id,
                curriculum_code=meta.curriculum_code,
                metadata={"category": meta.category, "credits": meta.credits},
            )
            success += 1
        except Exception:
            logger.error("DB upsert failed for %s", course_code, exc_info=True)
            failure += 1

    return success, failure
