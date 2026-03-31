import { useCallback, useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"
import type { UserEnrollment } from "@/lib/database.types"
import { useAuth } from "./use-auth"

const LOCAL_STORAGE_KEY = "TIME_ENROLLMENTS"
const AUTH_STORAGE_KEY_PREFIX = "TIME_ENROLLMENTS_AUTH_"

type EnrollmentsCacheEntry = {
  data: UserEnrollment[]
  hasLoaded: boolean
  isLoading: boolean
  error: Error | null
  promise: Promise<void> | null
}

const LOCAL_CACHE_KEY = "__local__"
const enrollmentCache = new Map<string, EnrollmentsCacheEntry>()
const enrollmentListeners = new Set<() => void>()

function emitEnrollmentsChange() {
  enrollmentListeners.forEach((listener) => listener())
}

function readLocalEnrollments(): UserEnrollment[] {
  const storedEnrollments = localStorage.getItem(LOCAL_STORAGE_KEY)
  if (!storedEnrollments) return []

  try {
    return JSON.parse(storedEnrollments) as UserEnrollment[]
  } catch (e) {
    console.error("Failed to parse local stored enrollments", e)
    return []
  }
}

function getAuthStorageKey(userId: string) {
  return `${AUTH_STORAGE_KEY_PREFIX}${userId}`
}

function readStoredEnrollments(storageKey: string): UserEnrollment[] {
  const storedEnrollments = localStorage.getItem(storageKey)
  if (!storedEnrollments) return []

  try {
    return JSON.parse(storedEnrollments) as UserEnrollment[]
  } catch (e) {
    console.error("Failed to parse stored enrollments", e)
    return []
  }
}

function writeStoredEnrollments(
  userId: string | null | undefined,
  enrollments: UserEnrollment[]
) {
  const storageKey = userId ? getAuthStorageKey(userId) : LOCAL_STORAGE_KEY
  localStorage.setItem(storageKey, JSON.stringify(enrollments))
}

function getCacheKey(userId: string | null | undefined) {
  return userId ?? LOCAL_CACHE_KEY
}

function getEnrollmentCache(userId: string | null | undefined) {
  const key = getCacheKey(userId)
  const existing = enrollmentCache.get(key)
  if (existing) return existing

  const created: EnrollmentsCacheEntry = {
    data: userId ? readStoredEnrollments(getAuthStorageKey(userId)) : readLocalEnrollments(),
    hasLoaded: !userId,
    isLoading: false,
    error: null,
    promise: null,
  }
  enrollmentCache.set(key, created)
  return created
}

function getEnrollmentsSnapshot(userId: string | null | undefined) {
  const cache = getEnrollmentCache(userId)
  return {
    enrollments: cache.data,
    isLoading: cache.isLoading,
    error: cache.error,
  }
}

async function fetchEnrollmentsOnce(userId: string) {
  const cache = getEnrollmentCache(userId)
  if (cache.promise) return cache.promise
  if (cache.hasLoaded) return Promise.resolve()

  const storedEnrollments = readStoredEnrollments(getAuthStorageKey(userId))
  if (storedEnrollments.length > 0) {
    cache.data = storedEnrollments
    emitEnrollmentsChange()
  }

  cache.isLoading = true
  cache.error = null
  emitEnrollmentsChange()

  cache.promise = (async () => {
    const { data, error } = await supabase
      .from("user_enrollments")
      .select("*")
      .eq("user_id", userId)

    if (error) {
      cache.error = new Error(error.message)
      cache.hasLoaded = false
      cache.isLoading = false
      emitEnrollmentsChange()
      return
    }

    cache.data = data ?? []
    writeStoredEnrollments(userId, cache.data)
    cache.hasLoaded = true
    cache.error = null
    cache.isLoading = false
    emitEnrollmentsChange()
  })().finally(() => {
    cache.promise = null
  })

  return cache.promise
}

export function useEnrollments() {
  const { user } = useAuth()

  const [state, setState] = useState(() =>
    getEnrollmentsSnapshot(user?.id ?? null)
  )

  useEffect(() => {
    const handleChange = () => {
      setState(getEnrollmentsSnapshot(user?.id ?? null))
    }

    enrollmentListeners.add(handleChange)
    handleChange()

    if (user) {
      void fetchEnrollmentsOnce(user.id)
    } else {
      const localCache = getEnrollmentCache(null)
      localCache.data = readLocalEnrollments()
      localCache.hasLoaded = true
      localCache.error = null
      localCache.isLoading = false
      emitEnrollmentsChange()
    }

    return () => {
      enrollmentListeners.delete(handleChange)
    }
  }, [user])

  const enrolledCourseIds = new Set(state.enrollments.map((e) => e.course_id))

  const addEnrollment = useCallback(
    async (courseId: string) => {
      const cache = getEnrollmentCache(user?.id ?? null)
      const newEnrollment: UserEnrollment = {
        user_id: user?.id ?? "local-user",
        course_id: courseId,
        enrolled_at: new Date().toISOString(),
      }

      // Optimistic update
      cache.data = [...cache.data, newEnrollment]
      cache.hasLoaded = true
      cache.error = null
      writeStoredEnrollments(user?.id ?? null, cache.data)
      emitEnrollmentsChange()

      if (!user) return

      const { error: err } = await supabase
        .from("user_enrollments")
        .insert({ user_id: user.id, course_id: courseId })

      if (err) {
        // Rollback
        cache.data = cache.data.filter((e) => e.course_id !== courseId)
        writeStoredEnrollments(user.id, cache.data)
        cache.error = new Error(err.message)
        emitEnrollmentsChange()
      }
    },
    [user]
  )

  const removeEnrollment = useCallback(
    async (courseId: string) => {
      const cache = getEnrollmentCache(user?.id ?? null)
      // Save for rollback
      const previous = cache.data

      // Optimistic update
      cache.data = cache.data.filter((e) => e.course_id !== courseId)
      cache.hasLoaded = true
      cache.error = null
      writeStoredEnrollments(user?.id ?? null, cache.data)
      emitEnrollmentsChange()

      if (!user) return

      const { error: err } = await supabase
        .from("user_enrollments")
        .delete()
        .eq("user_id", user.id)
        .eq("course_id", courseId)

      if (err) {
        // Rollback
        cache.data = previous
        writeStoredEnrollments(user.id, cache.data)
        cache.error = new Error(err.message)
        emitEnrollmentsChange()
      }
    },
    [user]
  )

  return {
    enrollments: state.enrollments,
    enrolledCourseIds,
    isLoading: state.isLoading,
    error: state.error,
    addEnrollment,
    removeEnrollment,
  }
}
