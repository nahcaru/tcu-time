/**
 * ユーザー設定 hook
 *
 * Manages user preferences stored in Supabase.
 * - Selected target/department
 * - Earned credits per category
 */
import { useCallback, useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"
import type { UserSettings } from "@/lib/database.types"
import { useAuth } from "./use-auth"

export interface EarnedCredits {
  practical: number
  research: number
  lectures: number
}

const LOCAL_STORAGE_KEY = "TIME_SETTINGS"

export function useSettings() {
  const { user } = useAuth()
  
  // Lazily initialize local storage state to avoid sync setState in useEffect
  const [settings, setSettings] = useState<UserSettings | null>(() => {
    if (!user) {
      const storedSettings = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (storedSettings) {
        try {
          return JSON.parse(storedSettings)
        } catch (e) {
          console.error("Failed to parse local stored settings", e)
        }
      }
    }
    return null
  })
  
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!user) return

    let cancelled = false

    async function fetch() {
      setIsLoading(true)

      const { data, error } = await supabase
        .from("user_settings")
        .select("*")
        .eq("user_id", user!.id)
        .maybeSingle()

      if (cancelled) return

      if (!error && data) {
        setSettings(data)
      } else if (!data) {
         setSettings(null)
      }
      setIsLoading(false)
    }

    fetch()
    return () => {
      cancelled = true
    }
  }, [user])

  const updateSettings = useCallback(
    async (updates: Partial<Pick<UserSettings, "department" | "earned_credits" | "theme">>) => {
      // Create new settings to optimistic update
      const newSettings = {
        ...settings,
        ...updates,
      } as UserSettings
      
      setSettings(newSettings)
      
      if (!user) {
        // Unauthenticated user - save to localStorage
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(newSettings))
        return
      }

      const payload = {
        ...settings, // Spread the original settings to avoid overwriting unchanged fields with defaults
        ...updates,
        user_id: user.id,
        updated_at: new Date().toISOString(),
      }

      const { data, error } = await supabase
        .from("user_settings")
        .upsert(payload, { onConflict: "user_id" })
        .select()
        .single()

      if (!error && data) {
        setSettings(data)
      }
    },
    [user, settings]
  )

  return { settings, isLoading, updateSettings }
}
