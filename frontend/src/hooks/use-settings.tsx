/**
 * ユーザー設定 Context & Hook
 *
 * Manages user preferences stored in Supabase with shared state across components.
 * - Selected target/department
 * - Earned credits per category
 */
import { createContext, useContext, useCallback, useEffect, useState, ReactNode } from "react"
import { supabase } from "@/lib/supabase"
import type { UserSettings } from "@/lib/database.types"
import { useAuth } from "./use-auth"

export interface EarnedCredits {
  practical: number
  research: number
  lectures: number
}

interface SettingsContextType {
  settings: UserSettings | null
  isLoading: boolean
  updateSettings: (
    updates: Partial<Pick<UserSettings, "department" | "earned_credits" | "theme">>
  ) => Promise<void>
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

const LOCAL_STORAGE_KEY = "TIME_SETTINGS"

export function SettingsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  
  // Lazily initialize local storage state to avoid sync setState in useEffect
  const [settings, setSettings] = useState<UserSettings | null>(() => {
    if (!user) {
      const storedSettings = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (storedSettings) {
        try {
          return JSON.parse(storedSettings) as UserSettings
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
        setSettings(data as UserSettings)
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
        ...settings, 
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
        setSettings(data as UserSettings)
      }
    },
    [user, settings]
  )

  return (
    <SettingsContext.Provider value={{ settings, isLoading, updateSettings }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (context === undefined) {
    throw new Error("useSettings must be used within a SettingsProvider")
  }
  return context
}
