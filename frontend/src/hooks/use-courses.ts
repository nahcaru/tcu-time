/**
 * 科目データ取得 hook
 *
 * Fetches course data from Supabase via PostgREST.
 * Supports filtering by target (department), term, category.
 * Search by course name and instructor.
 */

// Phase 2 implementation
export function useCourses() {
  return {
    courses: [],
    isLoading: false,
    error: null,
  }
}
