/**
 * Supabase Auth hook
 *
 * Manages authentication state.
 * - Current user
 * - Sign in / sign out
 * - Auth state change listener
 */

// Phase 4 implementation
export function useAuth() {
  return {
    user: null,
    isLoading: false,
    signOut: async () => {},
  }
}
