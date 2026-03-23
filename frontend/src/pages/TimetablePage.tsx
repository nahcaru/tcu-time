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
import { PageHeader } from "@/components/layout/PageHeader"

export function TimetablePage() {
  const { enrolledCourseIds, addEnrollment, removeEnrollment } =
    useEnrollments()
  const { courses: allCourses } = useCourses()

  // Filter to only enrolled courses
  const enrolledCourses = useMemo(
    () => allCourses.filter((c) => enrolledCourseIds.has(c.id)),
    [allCourses, enrolledCourseIds]
  )

  // Intensive courses = those with 集中 in their term
  const intensiveCourses = (terms: readonly string[]) =>
    enrolledCourses.filter((c) =>
      c.term != null && terms.includes(c.term) && c.term.includes("集中")
    )

  // Regular (non-intensive) enrolled courses for grid display
  const regularCourses = (terms: readonly string[]) =>
    enrolledCourses.filter((c) =>
      c.term != null && terms.includes(c.term) && !c.term.includes("集中")
    )

  return (
    <Tabs
      defaultValue="spring"
      className="relative flex min-h-full flex-col pb-6"
    >
      <PageHeader title="時間割">
        <TabsList className="w-full">
          <TabsTrigger value="spring">前期</TabsTrigger>
          <TabsTrigger value="fall">後期</TabsTrigger>
        </TabsList>
      </PageHeader>

      <div className="flex min-h-full w-full flex-1 flex-col px-4 pt-14 md:px-6 md:pt-0">
        <TabsContent value="spring">
          <SemesterContent
            regularCourses={
              regularCourses(SPRING_TERMS) as CourseWithRelations[]
            }
            intensiveCourses={
              intensiveCourses(SPRING_TERMS) as CourseWithRelations[]
            }
            enrolledCourses={enrolledCourses}
            firstHalfTerms={["前期前", "前期"]}
            secondHalfTerms={["前期後", "前期"]}
            termType="前期"
            addEnrollment={addEnrollment}
            removeEnrollment={removeEnrollment}
            enrolledCourseIds={enrolledCourseIds}
          />
        </TabsContent>

        <TabsContent value="fall" className="mt-0">
          <SemesterContent
            regularCourses={regularCourses(FALL_TERMS) as CourseWithRelations[]}
            intensiveCourses={
              intensiveCourses(FALL_TERMS) as CourseWithRelations[]
            }
            enrolledCourses={enrolledCourses}
            firstHalfTerms={["後期前", "後期"]}
            secondHalfTerms={["後期後", "後期"]}
            termType="後期"
            addEnrollment={addEnrollment}
            removeEnrollment={removeEnrollment}
            enrolledCourseIds={enrolledCourseIds}
          />
        </TabsContent>
      </div>
    </Tabs>
  )
}

function SemesterContent({
  regularCourses,
  intensiveCourses,
  enrolledCourses,
  firstHalfTerms,
  secondHalfTerms,
  termType,
  addEnrollment,
  removeEnrollment,
  enrolledCourseIds,
}: {
  regularCourses: CourseWithRelations[]
  intensiveCourses: CourseWithRelations[]
  enrolledCourses: CourseWithRelations[]
  firstHalfTerms: string[]
  secondHalfTerms: string[]
  termType: "前期" | "後期"
  addEnrollment: (courseId: string) => Promise<void>
  removeEnrollment: (courseId: string) => Promise<void>
  enrolledCourseIds: Set<string>
}) {
  return (
    <div className="flex flex-col gap-6">
      <TimeSlots />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <CourseGrid
          title="前半"
          terms={firstHalfTerms}
          enrolledCourses={regularCourses}
          addEnrollment={addEnrollment}
          removeEnrollment={removeEnrollment}
          enrolledCourseIds={enrolledCourseIds}
        />
        <CourseGrid
          title="後半"
          terms={secondHalfTerms}
          enrolledCourses={regularCourses}
          addEnrollment={addEnrollment}
          removeEnrollment={removeEnrollment}
          enrolledCourseIds={enrolledCourseIds}
        />
        <IntensiveCourses
          courses={intensiveCourses}
          terms={termType === "前期" ? ["前集中"] : ["後集中"]}
          addEnrollment={addEnrollment}
          removeEnrollment={removeEnrollment}
          enrolledCourseIds={enrolledCourseIds}
        />
        <CreditsTable termType={termType} enrolledCourses={enrolledCourses} />
      </div>
    </div>
  )
}
