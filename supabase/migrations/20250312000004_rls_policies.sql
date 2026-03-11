-- Row-Level Security policies

-- Courses: publicly readable
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "courses_read" ON courses FOR SELECT USING (true);

ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "schedules_read" ON schedules FOR SELECT USING (true);

ALTER TABLE course_targets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "course_targets_read" ON course_targets FOR SELECT USING (true);

ALTER TABLE course_metadata ENABLE ROW LEVEL SECURITY;
CREATE POLICY "course_metadata_read" ON course_metadata FOR SELECT USING (true);

-- User enrollments: own data only
ALTER TABLE user_enrollments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "enrollments_select" ON user_enrollments
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "enrollments_insert" ON user_enrollments
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "enrollments_delete" ON user_enrollments
  FOR DELETE USING (auth.uid() = user_id);

-- User settings: own data only
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "settings_select" ON user_settings
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "settings_insert" ON user_settings
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "settings_update" ON user_settings
  FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Extractions: admin only
ALTER TABLE extractions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "extractions_admin_read" ON extractions
  FOR SELECT USING (auth.jwt() ->> 'role' = 'admin');
CREATE POLICY "extractions_admin_write" ON extractions
  FOR ALL USING (auth.jwt() ->> 'role' = 'admin');

-- PDF links: admin only
ALTER TABLE pdf_links ENABLE ROW LEVEL SECURITY;
CREATE POLICY "pdf_links_admin" ON pdf_links
  FOR ALL USING (auth.jwt() ->> 'role' = 'admin');
