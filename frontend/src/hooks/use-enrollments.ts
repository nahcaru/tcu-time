/**
 * 登録科目 CRUD hook
 *
 * Manages user course enrollments via Supabase.
 * Requires authenticated user — returns empty state if not logged in.
 */
import { useCallback, useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"
import type { UserEnrollment } from "@/lib/database.types"
import { useAuth } from "./use-auth"

export function useEnrollments() {
  const { user } = useAuth()
  const [enrollments, setEnrollments] = useState<UserEnrollment[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!user) return

    let cancelled = false

    async function fetchEnrollments() {
      setIsLoading(true)
      setError(null)

      const { data, error: err } = await supabase
        .from("user_enrollments")
        .select("*")
        .eq("user_id", user!.id)

      if (cancelled) return

      if (err) {
        setError(new Error(err.message))
        setIsLoading(false)
        return
      }

      setEnrollments(data ?? [])
      setIsLoading(false)
    }

    fetchEnrollments()
    return () => {
      cancelled = true
    }
  }, [user])

  // Reset enrollments on sign-out (derived from user state, not in effect)
  const activeEnrollments = user ? enrollments : []

  const enrolledCourseIds = new Set(activeEnrollments.map((e) => e.course_id))

  const addEnrollment = useCallback(
    async (courseId: string) => {
      if (!user) return

      const newEnrollment: UserEnrollment = {
        user_id: user.id,
        course_id: courseId,
        enrolled_at: new Date().toISOString(),
      }

      // Optimistic update
      setEnrollments((prev) => [...prev, newEnrollment])

      const { error: err } = await supabase
        .from("user_enrollments")
        .insert({ user_id: user.id, course_id: courseId })

      if (err) {
        // Rollback
        setEnrollments((prev) =>
          prev.filter((e) => e.course_id !== courseId)
        )
        setError(new Error(err.message))
      }
    },
    [user]
  )

  const removeEnrollment = useCallback(
    async (courseId: string) => {
      if (!user) return

      // Save for rollback
      const previous = enrollments

      // Optimistic update
      setEnrollments((prev) =>
        prev.filter((e) => e.course_id !== courseId)
      )

      const { error: err } = await supabase
        .from("user_enrollments")
        .delete()
        .eq("user_id", user.id)
        .eq("course_id", courseId)

      if (err) {
        // Rollback
        setEnrollments(previous)
        setError(new Error(err.message))
      }
    },
    [user, enrollments]
  )

  return {
    enrollments: activeEnrollments,
    enrolledCourseIds,
    isLoading,
    error,
    addEnrollment,
    removeEnrollment,
  }
}
