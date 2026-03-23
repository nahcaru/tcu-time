-- Add missing columns to extractions table and admin write RLS policies

-- 1. extractions テーブルに不足カラム追加
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS pdf_type TEXT;
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS semester TEXT;
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS is_tentative BOOLEAN DEFAULT false;
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS academic_year INTEGER;

-- 2. courses/schedules/course_targets/course_metadata に admin 書き込みポリシー追加
CREATE POLICY "courses_admin_write" ON courses
  FOR ALL USING (auth.jwt() -> 'app_metadata' ->> 'role' = 'admin');

CREATE POLICY "schedules_admin_write" ON schedules
  FOR ALL USING (auth.jwt() -> 'app_metadata' ->> 'role' = 'admin');

CREATE POLICY "course_targets_admin_write" ON course_targets
  FOR ALL USING (auth.jwt() -> 'app_metadata' ->> 'role' = 'admin');

CREATE POLICY "course_metadata_admin_write" ON course_metadata
  FOR ALL USING (auth.jwt() -> 'app_metadata' ->> 'role' = 'admin');
