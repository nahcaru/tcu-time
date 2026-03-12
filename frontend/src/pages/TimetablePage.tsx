import { useMemo } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TimeSlots } from "@/components/timetable/TimeSlots"
import { CourseGrid } from "@/components/timetable/CourseGrid"
import { IntensiveCourses } from "@/components/timetable/IntensiveCourses"
import { CreditsTable } from "@/components/timetable/CreditsTable"
import { useCourses } from "@/hooks/use-courses"
import { useEnrollments } from "@/hooks/use-enrollments"
import { SPRING_TERMS, FALL_TERMS } from "@/lib/constants"
import type { CourseWithRelations } from "@/lib/database.types"

export function TimetablePage() {
  const { enrolledCourseIds } = useEnrollments()
  const { courses: allCourses } = useCourses()

  // Filter to only enrolled courses
  const enrolledCourses = useMemo(
    () => allCourses.filter((c) => enrolledCourseIds.has(c.id)),
    [allCourses, enrolledCourseIds]
  )

  // Intensive courses = those with 集中 in their term
  const intensiveCourses = (terms: readonly string[]) =>
    enrolledCourses.filter((c) =>
      c.schedules.some(
        (s) => terms.includes(s.term) && s.term.includes("集中")
      )
    )

  // Regular (non-intensive) enrolled courses for grid display
  const regularCourses = (terms: readonly string[]) =>
    enrolledCourses.filter((c) =>
      c.schedules.some(
        (s) => terms.includes(s.term) && !s.term.includes("集中")
      )
    )

  return (
    <div className="flex flex-col h-full bg-background md:-mx-6 md:-mt-6 md:p-6 lg:p-0">
      <div className="flex flex-col gap-6 lg:p-6 lg:pl-8">
        <Tabs defaultValue="spring" className="w-full">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold tracking-tight">時間割</h1>
            <TabsList>
              <TabsTrigger value="spring">前期</TabsTrigger>
              <TabsTrigger value="fall">後期</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="spring" className="mt-0">
            <SemesterContent
              regularCourses={regularCourses(SPRING_TERMS) as CourseWithRelations[]}
              intensiveCourses={intensiveCourses(SPRING_TERMS) as CourseWithRelations[]}
              enrolledCourses={enrolledCourses}
              firstHalfTerms={["前期前", "前期"]}
              secondHalfTerms={["前期後", "前期"]}
              termType="前期"
            />
          </TabsContent>

          <TabsContent value="fall" className="mt-0">
            <SemesterContent
              regularCourses={regularCourses(FALL_TERMS) as CourseWithRelations[]}
              intensiveCourses={intensiveCourses(FALL_TERMS) as CourseWithRelations[]}
              enrolledCourses={enrolledCourses}
              firstHalfTerms={["後期前", "後期"]}
              secondHalfTerms={["後期後", "後期"]}
              termType="後期"
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

function SemesterContent({
  regularCourses,
  intensiveCourses,
  enrolledCourses,
  firstHalfTerms,
  secondHalfTerms,
  termType,
}: {
  regularCourses: CourseWithRelations[]
  intensiveCourses: CourseWithRelations[]
  enrolledCourses: CourseWithRelations[]
  firstHalfTerms: string[]
  secondHalfTerms: string[]
  termType: "前期" | "後期"
}) {
  return (
    <div className="flex flex-col gap-6">
      <TimeSlots />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <CourseGrid
          title="前半"
          terms={firstHalfTerms}
          enrolledCourses={regularCourses}
        />
        <CourseGrid
          title="後半"
          terms={secondHalfTerms}
          enrolledCourses={regularCourses}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <IntensiveCourses courses={intensiveCourses} />
        </div>
        <div className="lg:col-span-2">
          <CreditsTable
            termType={termType}
            enrolledCourses={enrolledCourses}
          />
        </div>
      </div>
    </div>
  )
}
