-- =====================================================================
-- Review page redesign: schema changes
-- 1. courses に term / room を追加（schedules から移動）
-- 2. schedules の UNIQUE制約を (course_id, day, period) に変更し term/room を削除
-- 3. courses の UNIQUE を code → (code, academic_year) に変更
-- 4. extractions.status から rejected / pending_review を廃止
-- =====================================================================

-- 1. courses に term / room カラムを追加
ALTER TABLE courses
  ADD COLUMN term TEXT DEFAULT '',
  ADD COLUMN room TEXT DEFAULT '';

-- 2a. schedules の旧 UNIQUE 制約を削除
ALTER TABLE schedules
  DROP CONSTRAINT schedules_course_id_term_day_period_key;

-- 2b. schedules の term / room カラムを削除（courses に移動）
ALTER TABLE schedules
  DROP COLUMN term,
  DROP COLUMN room;

-- 2c. schedules に新 UNIQUE 制約 (course_id, day, period) を追加
ALTER TABLE schedules
  ADD CONSTRAINT schedules_course_id_day_period_key UNIQUE (course_id, day, period);

-- 3a. courses の旧 UNIQUE (code) を削除
ALTER TABLE courses
  DROP CONSTRAINT courses_code_key;

-- 3b. courses に新 UNIQUE (code, academic_year) を追加
ALTER TABLE courses
  ADD CONSTRAINT courses_code_academic_year_key UNIQUE (code, academic_year);

-- 4. extractions.status の CHECK 制約を更新（rejected / pending_review を廃止）
--    既存の rejected 行を extracted（承認待ち）に移行
UPDATE extractions SET status = 'extracted' WHERE status IN ('rejected', 'pending_review');

ALTER TABLE extractions DROP CONSTRAINT extractions_status_check;
ALTER TABLE extractions
  ADD CONSTRAINT extractions_status_check
    CHECK (status IN ('pending', 'extracted', 'approved'));
