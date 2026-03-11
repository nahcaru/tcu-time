/**
 * 登録科目 CRUD hook
 *
 * Manages user course enrollments via Supabase.
 * - Add enrollment
 * - Remove enrollment
 * - List user enrollments
 */

// Phase 3 implementation
export function useEnrollments() {
  return {
    enrollments: [],
    isLoading: false,
    error: null,
    addEnrollment: async (_courseId: string) => {},
    removeEnrollment: async (_courseId: string) => {},
  }
}
