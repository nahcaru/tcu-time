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

export function useSettings() {
  const { user } = useAuth()
  const [settings, setSettings] = useState<UserSettings | null>(null)
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
      if (!user) return

      const payload = {
        user_id: user.id,
        ...updates,
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
    [user]
  )

  const activeSettings = user ? settings : null

  return { settings: activeSettings, isLoading, updateSettings }
}
