-- Pipeline improvements: add columns for PDF type tracking, tentative courses, and advance enrollment
-- Timestamp: 2025-03-14

-- 1. ALTER extractions table - add PDF type tracking and semester info
ALTER TABLE extractions
  ADD COLUMN pdf_type TEXT NOT NULL DEFAULT 'timetable'
    CHECK (pdf_type IN ('timetable', 'changelog', 'advance_enrollment')),
  ADD COLUMN semester TEXT NOT NULL DEFAULT 'spring'
    CHECK (semester IN ('spring', 'fall')),
  ADD COLUMN is_tentative BOOLEAN DEFAULT false,
  ADD COLUMN academic_year INT;

-- 2. ALTER courses table - add source tracking and status management
ALTER TABLE courses
  ADD COLUMN source_type TEXT DEFAULT 'timetable',
  ADD COLUMN is_tentative BOOLEAN DEFAULT false,
  ADD COLUMN advance_enrollment BOOLEAN DEFAULT false,
  ADD COLUMN status TEXT DEFAULT 'active'
    CHECK (status IN ('active', 'cancelled'));

-- 3. ALTER pdf_links table - add PDF type and semester tracking
ALTER TABLE pdf_links
  ADD COLUMN pdf_type TEXT,
  ADD COLUMN semester TEXT;

-- 4. Add useful indexes for common queries
CREATE INDEX idx_courses_semester_tentative ON courses(academic_year, is_tentative) WHERE is_tentative = true;
CREATE INDEX idx_courses_advance ON courses(advance_enrollment) WHERE advance_enrollment = true;
CREATE INDEX idx_extractions_type ON extractions(pdf_type, semester);
