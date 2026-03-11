-- Extractions: pipeline run tracking (must be created before courses)
CREATE TABLE extractions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pdf_url      TEXT NOT NULL,
  pdf_hash     TEXT NOT NULL,
  status       TEXT DEFAULT 'pending'
               CHECK (status IN ('pending','extracted','pending_review','approved','rejected')),
  raw_json     JSONB,
  error_log    TEXT,
  reviewed_by  UUID REFERENCES auth.users(id),
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now()
);

-- Courses
CREATE TABLE courses (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code          TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  instructors   TEXT[] NOT NULL,
  year_level    INT DEFAULT 1,
  class_section TEXT DEFAULT '',
  academic_year INT NOT NULL,
  notes         TEXT DEFAULT '',
  extraction_id UUID REFERENCES extractions(id),
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_courses_code ON courses(code);
CREATE INDEX idx_courses_academic_year ON courses(academic_year);

-- Schedules: one course can have multiple time slots (paired lectures)
CREATE TABLE schedules (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id  UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  term       TEXT NOT NULL,
  day        TEXT NOT NULL CHECK (day IN ('月','火','水','木','金','土')),
  period     INT NOT NULL CHECK (period BETWEEN 1 AND 5),
  room       TEXT DEFAULT '',
  UNIQUE(course_id, term, day, period)
);

CREATE INDEX idx_schedules_slot ON schedules(term, day, period);
CREATE INDEX idx_schedules_course ON schedules(course_id);

-- Course targets: which departments a course is aimed at
CREATE TABLE course_targets (
  course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  target_code TEXT NOT NULL,
  target_name TEXT NOT NULL,
  note        TEXT DEFAULT '',
  PRIMARY KEY(course_id, target_code)
);

-- Course metadata: per curriculum code (from syllabus scraping)
CREATE TABLE course_metadata (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  curriculum_code TEXT NOT NULL,
  category        TEXT,
  compulsoriness  TEXT,
  credits         DECIMAL(3,1),
  syllabus_url    TEXT,
  UNIQUE(course_id, curriculum_code)
);

CREATE INDEX idx_metadata_course ON course_metadata(course_id);
CREATE INDEX idx_metadata_curriculum ON course_metadata(curriculum_code);
