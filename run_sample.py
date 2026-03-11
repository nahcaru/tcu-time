"""Run the pipeline locally: extract from reference PDF, enrich a few courses, save to JSON."""

import json
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from pipeline.extractor import extract_courses_from_pdf
from pipeline.enricher import scrape_syllabus

REFERENCE_PDF = Path(__file__).parent / "References" / "grad_timetable_front.pdf"
OUTPUT_FILE = Path(__file__).parent / "pipeline" / "sample_output.json"
ENRICH_COUNT = 5
ACADEMIC_YEAR = 2025
SCRAPE_DELAY = 3.0


def main() -> None:
    # --- Extract ---
    logger.info("Reading reference PDF: %s", REFERENCE_PDF)
    pdf_bytes = REFERENCE_PDF.read_bytes()
    courses = extract_courses_from_pdf(pdf_bytes)
    logger.info("Extracted %d courses", len(courses))

    # --- Enrich a sample ---
    sample = courses[:ENRICH_COUNT]
    enriched = []

    for i, course in enumerate(sample):
        logger.info("[%d/%d] Enriching %s (%s)", i + 1, ENRICH_COUNT, course.code, course.name)
        meta = scrape_syllabus(ACADEMIC_YEAR, course.code)

        entry = course.model_dump()
        entry["schedules"] = [s.model_dump() for s in course.schedules]
        entry["targets"] = [t.model_dump() for t in course.targets]

        if meta:
            entry["metadata"] = meta.model_dump()
            logger.info("  -> category=%s, credits=%s", meta.category, meta.credits)
        else:
            entry["metadata"] = None
            logger.warning("  -> enrichment failed")

        enriched.append(entry)

        if i < ENRICH_COUNT - 1:
            time.sleep(SCRAPE_DELAY)

    # --- Also include remaining courses without enrichment ---
    remaining = [c.model_dump() for c in courses[ENRICH_COUNT:]]

    result = {
        "academic_year": ACADEMIC_YEAR,
        "total_courses": len(courses),
        "enriched_count": len([e for e in enriched if e.get("metadata")]),
        "enriched_courses": enriched,
        "all_courses": [c.model_dump() for c in courses],
    }

    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved results to %s", OUTPUT_FILE)
    logger.info("Summary: %d total, %d enriched", result["total_courses"], result["enriched_count"])


if __name__ == "__main__":
    main()
