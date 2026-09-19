-- Add published_at column to extractions table
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

-- Allow semester to be NULL for full-year / advance enrollment PDFs
ALTER TABLE extractions ALTER COLUMN semester DROP NOT NULL;
ALTER TABLE extractions DROP CONSTRAINT IF EXISTS extractions_semester_check;
ALTER TABLE extractions ADD CONSTRAINT extractions_semester_check CHECK (semester IS NULL OR semester IN ('spring', 'fall'));

-- Update existing 2026 academic year records with actual release/publication dates
UPDATE extractions
SET published_at = '2026-09-10T18:43:34+09:00'
WHERE pdf_type = 'timetable' AND semester = 'fall' AND academic_year = 2026;

UPDATE extractions
SET published_at = '2026-04-15T18:09:20+09:00'
WHERE pdf_type = 'timetable' AND semester = 'spring' AND academic_year = 2026;

UPDATE extractions
SET published_at = '2026-03-26T14:51:00+09:00', semester = NULL
WHERE pdf_type = 'advance_enrollment' AND academic_year = 2026;

-- Update existing 2025 academic year records
UPDATE extractions
SET published_at = '2025-09-16T00:00:00+09:00'
WHERE pdf_type = 'timetable' AND semester = 'fall' AND academic_year = 2025;

UPDATE extractions
SET published_at = '2025-03-25T00:00:00+09:00'
WHERE pdf_type = 'timetable' AND semester = 'spring' AND academic_year = 2025;

UPDATE extractions
SET published_at = '2025-05-01T00:00:00+09:00'
WHERE pdf_type = 'changelog' AND academic_year = 2025;

UPDATE extractions
SET published_at = '2025-03-25T00:00:00+09:00', semester = NULL
WHERE pdf_type = 'advance_enrollment' AND academic_year = 2025;
