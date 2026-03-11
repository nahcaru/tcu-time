/**
 * ユーザー設定 hook
 *
 * Manages user preferences stored in Supabase.
 * - Selected major
 * - Earned credits per category
 */

// Phase 3 implementation
export function useSettings() {
  return {
    settings: null,
    isLoading: false,
    updateSettings: async (_settings: Record<string, unknown>) => {},
  }
}
