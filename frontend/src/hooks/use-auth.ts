import { useCallback, useEffect, useState } from "react"
import type { User } from "@supabase/supabase-js"
import { supabase } from "@/lib/supabase"
import type { UserSettings, UserEnrollment } from "@/lib/database.types"

const LOCAL_SETTINGS_KEY = "TIME_SETTINGS"
const LOCAL_ENROLLMENTS_KEY = "TIME_ENROLLMENTS"

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const syncLocalData = async (authUser: User) => {
    // 1. Sync Settings
    const storedSettings = localStorage.getItem(LOCAL_SETTINGS_KEY)
    if (storedSettings) {
      try {
        const parsedSettings = JSON.parse(storedSettings) as UserSettings
        
        // Fetch existing remote settings to merge
        const { data: remoteSettings } = await supabase
          .from("user_settings")
          .select("*")
          .eq("user_id", authUser.id)
          .maybeSingle()

        const payload = {
          ...remoteSettings,
          ...parsedSettings,
          user_id: authUser.id,
          updated_at: new Date().toISOString(),
        }

        await supabase
          .from("user_settings")
          .upsert(payload, { onConflict: "user_id" })
          
        localStorage.removeItem(LOCAL_SETTINGS_KEY)
      } catch (e) {
        console.error("Failed to sync local settings", e)
      }
    }

    // 2. Sync Enrollments
    const storedEnrollments = localStorage.getItem(LOCAL_ENROLLMENTS_KEY)
    if (storedEnrollments) {
      try {
        const parsedEnrollments = JSON.parse(storedEnrollments) as UserEnrollment[]
        
        if (parsedEnrollments.length > 0) {
          const enrollmentsPayload = parsedEnrollments.map((e) => ({
            user_id: authUser.id,
            course_id: e.course_id,
            enrolled_at: e.enrolled_at,
          }))

          // For enrollments, we use insert with onConflict ignore, but currently we just do a regular insert.
          // Since the PK is (user_id, course_id), we should upsert with `ignoreDuplicates: true` 
          // to prevent errors for already enrolled courses.
          await supabase
            .from("user_enrollments")
            .upsert(enrollmentsPayload, { onConflict: "user_id, course_id" })
        }
        
        localStorage.removeItem(LOCAL_ENROLLMENTS_KEY)
      } catch (e) {
        console.error("Failed to sync local enrollments", e)
      }
    }
  }

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setIsLoading(false)
      
      if (session?.user) {
        syncLocalData(session.user)
      }
    })

    // Listen for auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user ?? null)
      
      if (event === "SIGNED_IN" && session?.user) {
        syncLocalData(session.user)
      } else if (event === "SIGNED_OUT") {
        // Option: clear local storage if you want strict logout cleanup. 
        // We leave it to allow trying the app unauthenticated again.
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
  }, [])

  return { user, isLoading, signOut }
}
