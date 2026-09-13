import { createClient } from "@supabase/supabase-js"
import type { Database } from "./database.types"

const proc =
  typeof globalThis !== "undefined"
    ? (globalThis as { process?: { env?: Record<string, string | undefined> } })
        .process
    : undefined
const isTest = proc?.env?.NODE_ENV === "test"

const supabaseUrl =
  import.meta.env.VITE_SUPABASE_URL ||
  proc?.env?.VITE_SUPABASE_URL ||
  (isTest ? "https://placeholder.supabase.co" : "")
const supabaseKey =
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY ||
  proc?.env?.VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY ||
  (isTest ? "placeholder-key" : "")

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    "Missing VITE_SUPABASE_URL or VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY environment variables"
  )
}

export const supabase = createClient<Database>(supabaseUrl, supabaseKey)
