export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      course_metadata: {
        Row: {
          category: string | null
          course_id: string
          credits: number | null
          curriculum_code: string
          id: string
        }
        Insert: {
          category?: string | null
          course_id: string
          credits?: number | null
          curriculum_code?: string
          id?: string
        }
        Update: {
          category?: string | null
          course_id?: string
          credits?: number | null
          curriculum_code?: string
          id?: string
        }
        Relationships: [
          {
            foreignKeyName: "course_metadata_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
        ]
      }
      course_targets: {
        Row: {
          course_id: string
          note: string | null
          target_code: string
          target_name: string
        }
        Insert: {
          course_id: string
          note?: string | null
          target_code: string
          target_name: string
        }
        Update: {
          course_id?: string
          note?: string | null
          target_code?: string
          target_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "course_targets_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
        ]
      }
      courses: {
        Row: {
          academic_year: number
          class_section: string | null
          code: string
          created_at: string | null
          extraction_id: string | null
          id: string
          instructors: string[]
          name: string
          notes: string | null
          updated_at: string | null
          year_level: number | null
        }
        Insert: {
          academic_year: number
          class_section?: string | null
          code: string
          created_at?: string | null
          extraction_id?: string | null
          id?: string
          instructors: string[]
          name: string
          notes?: string | null
          updated_at?: string | null
          year_level?: number | null
        }
        Update: {
          academic_year?: number
          class_section?: string | null
          code?: string
          created_at?: string | null
          extraction_id?: string | null
          id?: string
          instructors?: string[]
          name?: string
          notes?: string | null
          updated_at?: string | null
          year_level?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "courses_extraction_id_fkey"
            columns: ["extraction_id"]
            isOneToOne: false
            referencedRelation: "extractions"
            referencedColumns: ["id"]
          },
        ]
      }
      extractions: {
        Row: {
          created_at: string | null
          error_log: string | null
          id: string
          pdf_hash: string
          pdf_url: string
          raw_json: Json | null
          reviewed_by: string | null
          status: string | null
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          error_log?: string | null
          id?: string
          pdf_hash: string
          pdf_url: string
          raw_json?: Json | null
          reviewed_by?: string | null
          status?: string | null
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          error_log?: string | null
          id?: string
          pdf_hash?: string
          pdf_url?: string
          raw_json?: Json | null
          reviewed_by?: string | null
          status?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      pdf_links: {
        Row: {
          hash: string
          id: string
          label: string | null
          updated_at: string | null
          url: string
        }
        Insert: {
          hash: string
          id?: string
          label?: string | null
          updated_at?: string | null
          url: string
        }
        Update: {
          hash?: string
          id?: string
          label?: string | null
          updated_at?: string | null
          url?: string
        }
        Relationships: []
      }
      schedules: {
        Row: {
          course_id: string
          day: string
          id: string
          period: number
          room: string | null
          term: string
        }
        Insert: {
          course_id: string
          day: string
          id?: string
          period: number
          room?: string | null
          term: string
        }
        Update: {
          course_id?: string
          day?: string
          id?: string
          period?: number
          room?: string | null
          term?: string
        }
        Relationships: [
          {
            foreignKeyName: "schedules_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
        ]
      }
      user_enrollments: {
        Row: {
          course_id: string
          enrolled_at: string | null
          user_id: string
        }
        Insert: {
          course_id: string
          enrolled_at?: string | null
          user_id: string
        }
        Update: {
          course_id?: string
          enrolled_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_enrollments_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
        ]
      }
      user_settings: {
        Row: {
          department: string | null
          earned_credits: Json | null
          theme: string | null
          updated_at: string | null
          user_id: string
        }
        Insert: {
          department?: string | null
          earned_credits?: Json | null
          theme?: string | null
          updated_at?: string | null
          user_id: string
        }
        Update: {
          department?: string | null
          earned_credits?: Json | null
          theme?: string | null
          updated_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

// Convenience type aliases
type PublicSchema = Database["public"]

export type Tables<T extends keyof PublicSchema["Tables"]> =
  PublicSchema["Tables"][T]["Row"]

export type TablesInsert<T extends keyof PublicSchema["Tables"]> =
  PublicSchema["Tables"][T]["Insert"]

export type TablesUpdate<T extends keyof PublicSchema["Tables"]> =
  PublicSchema["Tables"][T]["Update"]

// Domain types used across the app
export type Course = Tables<"courses">
export type Schedule = Tables<"schedules">
export type CourseTarget = Tables<"course_targets">
export type CourseMetadata = Tables<"course_metadata">
export type UserEnrollment = Tables<"user_enrollments">
export type UserSettings = Tables<"user_settings">
export type Extraction = Tables<"extractions">

/** Course with all joined relations */
export interface CourseWithRelations extends Course {
  schedules: Schedule[]
  course_targets: CourseTarget[]
  course_metadata: CourseMetadata[]
}
