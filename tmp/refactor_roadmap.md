# Pipeline Refactor Roadmap

## Goal

Refactor the pipeline toward an LLM-first extraction architecture:

- Keep deterministic parsing for HTML inputs only
- Use Gemini as the primary extraction engine for PDFs
- Separate orchestration, extraction, validation, persistence, and approval logic
- Reduce global state and duplicated utilities

## Target Structure

```text
pipeline/
  core/
    models.py
    settings.py
    academic_year.py
    normalize.py
    hash.py
  adapters/
    gemini.py
    http.py
    supabase_client.py
  extractors/
    timetable.py
    changelog.py
    advance.py
  parsers/
    monitor_page.py
    syllabus.py
  repositories/
    extractions.py
    pdf_links.py
    courses.py
    metadata.py
  services/
    monitor_service.py
    extraction_service.py
    approval_service.py
    enrichment_service.py
  cli/
    run_pipeline.py
```

## Principles

- PDFs: Gemini-first, schema-validated extraction
- HTML: deterministic parsing
- Repositories: data access only
- Services: workflow and business logic
- Core: shared domain types and utilities
- CLI: thin entrypoints only

## Phase 1: Shared Utilities and Settings

Create:

- `pipeline/core/settings.py`
- `pipeline/core/academic_year.py`
- `pipeline/core/hash.py`
- `pipeline/core/normalize.py`

Move:

- academic year detection from `main.py`, `extractor.py`, and `enricher.py`
- hash helpers from `monitor.py` and `extractor.py`
- normalization helpers from `extractor.py`
- config validation from `config.py`

Deliverable:

- One implementation per shared concern
- Temporary compatibility shims allowed

Risk: Low

## Phase 2: Repository Split

Split `pipeline/db.py` into:

- `repositories/extractions.py`
- `repositories/pdf_links.py`
- `repositories/courses.py`
- `repositories/metadata.py`

Keep `db.py` as a temporary facade during migration.

Deliverable:

- Supabase access isolated from workflow logic

Risk: Medium

## Phase 3: Approval Service

Create `pipeline/services/approval_service.py`.

Move:

- `_apply_timetable_approval`
- `_apply_changelog_approval`
- `_apply_advance_approval`
- `approve_extraction`

Deliverable:

- No approval workflow logic in the DB layer

Risk: Medium

## Phase 4: Shared Gemini Adapter

Create `pipeline/adapters/gemini.py`.

Unify:

- Gemini client creation
- PDF submission
- JSON extraction
- schema validation handoff
- retry and error handling

Deliverable:

- timetable, changelog, and advance extraction share one LLM boundary

Risk: Medium

## Phase 5: LLM Extractors

Create:

- `pipeline/extractors/timetable.py`
- `pipeline/extractors/changelog.py`
- `pipeline/extractors/advance.py`

Move from current modules:

- response schemas
- JSON parsing helpers
- output normalization
- public extract functions

Keep only the deterministic cleanup logic still needed after Gemini output.

Deliverable:

- PDF extraction modules are extractor-oriented, not parser-oriented

Risk: Medium

## Phase 6: Deterministic HTML Parsers

Create:

- `pipeline/parsers/monitor_page.py`
- `pipeline/parsers/syllabus.py`

Move:

- HTML traversal and extraction helpers from `monitor.py`
- syllabus HTML parsing helpers from `enricher.py`

Deliverable:

- deterministic parsing limited to HTML sources

Risk: Low

## Phase 7: Service Layer Split

Create:

- `pipeline/services/monitor_service.py`
- `pipeline/services/extraction_service.py`
- `pipeline/services/enrichment_service.py`

Move:

- `check_for_updates`
- extraction dispatch and save flow
- `enrich_courses`
- related coordination logic

Reduce `main.py` to a thin coordinator or move it to `cli/run_pipeline.py`.

Deliverable:

- orchestration modules mostly compose services

Risk: Medium

## Phase 8: Cleanup

Remove:

- compatibility shims
- dead parser-first PDF logic
- duplicate helpers and old import paths

Deliverable:

- final module structure is the only structure in use

Risk: Low

## Function-Level Migration Checklist

### Move to `core`

- academic year helpers from `main.py`, `extractor.py`, `enricher.py`
- normalization helpers from `extractor.py`
- hash helpers from `monitor.py`, `extractor.py`
- environment validation from `config.py`

### Move to `extractors`

- `extract_courses_from_pdf` and Gemini-facing timetable schemas/helpers
- `parse_changelog` and changelog response schemas
- `extract_course_names` and advance enrollment response schemas

### Move to `parsers`

- `extract_pdf_links`
- `extract_advance_pdf_links`
- `classify_pdf_link`
- syllabus field extraction helpers
- `parse_syllabus_html`

### Move to `repositories`

- extraction CRUD/status functions
- pdf link persistence
- course CRUD/update functions
- metadata upsert/query functions

### Move to `services`

- approval workflow
- extraction dispatch
- update monitoring flow
- enrichment orchestration

## Testing Strategy

Before each structural move, preserve behavior with characterization tests around:

- approval flow
- monitor update detection
- timetable extraction output shape
- changelog extraction output shape
- advance enrollment extraction output shape
- syllabus enrichment flow

After migration:

- parser tests should target pure HTML helpers
- extractor tests should mock Gemini at the adapter boundary
- service tests should mock repositories and adapters
- keep one smoke E2E flow for monitor -> extract -> enrich

## Suggested Execution Order

1. Phase 1: Shared utilities and settings
2. Phase 2: Repository split
3. Phase 3: Approval service
4. Phase 4: Shared Gemini adapter
5. Phase 6: Deterministic HTML parsers
6. Phase 5: LLM extractors
7. Phase 7: Service layer split
8. Phase 8: Cleanup

## Definition of Done

- `db.py` no longer contains approval workflow logic
- PDF extraction is Gemini-first and schema-validated
- HTML parsing is isolated in parser modules
- services own workflow logic
- shared helpers exist only once
- tests rely on stable boundaries instead of deep module patching
