import { useCallback, useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"
import type { UserEnrollment } from "@/lib/database.types"
import { useAuth } from "./use-auth"

const LOCAL_STORAGE_KEY = "TIME_ENROLLMENTS"

export function useEnrollments() {
  const { user } = useAuth()
  
  // Lazily initialize local storage state
  const [enrollments, setEnrollments] = useState<UserEnrollment[]>(() => {
    if (!user) {
      const storedEnrollments = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (storedEnrollments) {
        try {
          return JSON.parse(storedEnrollments)
        } catch (e) {
          console.error("Failed to parse local stored enrollments", e)
        }
      }
    }
    return []
  })
  
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

  const enrolledCourseIds = new Set(enrollments.map((e) => e.course_id))

  const addEnrollment = useCallback(
    async (courseId: string) => {
      const newEnrollment: UserEnrollment = {
        user_id: user?.id ?? "local-user",
        course_id: courseId,
        enrolled_at: new Date().toISOString(),
      }

      // Optimistic update
      setEnrollments((prev) => {
        const next = [...prev, newEnrollment]
        if (!user) {
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(next))
        }
        return next
      })

      if (!user) return

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
      // Save for rollback
      const previous = enrollments

      // Optimistic update
      setEnrollments((prev) => {
        const next = prev.filter((e) => e.course_id !== courseId)
        if (!user) {
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(next))
        }
        return next
      })

      if (!user) return

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
    enrollments,
    enrolledCourseIds,
    isLoading,
    error,
    addEnrollment,
    removeEnrollment,
  }
}
