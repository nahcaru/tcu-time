-- User enrollments
CREATE TABLE user_enrollments (
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  course_id  UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  enrolled_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY(user_id, course_id)
);

-- User settings
CREATE TABLE user_settings (
  user_id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  department      TEXT,
  theme           TEXT DEFAULT 'system' CHECK (theme IN ('system','light','dark')),
  earned_credits  JSONB DEFAULT '{}',
  updated_at      TIMESTAMPTZ DEFAULT now()
);
