import { createClient } from "@supabase/supabase-js"
import type { Database } from "./database.types"

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    "Missing VITE_SUPABASE_URL or VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY environment variables"
  )
}

export const supabase = createClient<Database>(supabaseUrl, supabaseKey)
