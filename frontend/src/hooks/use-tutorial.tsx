/* eslint-disable react-refresh/only-export-components */
/**
 * チュートリアル Context & Hook
 *
 * driver.js を使ったスポットライト型ツアーを管理する。
 * - CoursesPage / TimetablePage ごとに独立したツアーを定義
 * - localStorage で「完了済み」フラグを管理 (初回訪問時のみ自動起動)
 * - startTour / resetTour を Context 経由で各コンポーネントに提供
 */
import { createContext, useCallback, useContext, useRef } from "react"
import type { ReactNode } from "react"
import type { DriveStep } from "driver.js"

// ─── ツアー定義 ───────────────────────────────────────────────────────────────

const TOURS: Record<string, DriveStep[]> = {
  courses: [
    {
      element: "#tutorial-search",
      popover: {
        title: "科目を検索",
        description:
          "科目名や教員名でキーワード検索ができます。候補がサジェストされます。",
        side: "bottom",
        align: "start",
      },
    },
    {
      element: () => {
        const desktop = document.querySelector<HTMLElement>("#tutorial-filter")
        // offsetParent が null = display:none で非表示 (モバイル時の lg:hidden)
        if (desktop && desktop.offsetParent !== null) return desktop
        return document.querySelector("#tutorial-filter-mobile") as Element
      },
      popover: {
        title: "フィルター",
        description: "学期・対象学科・履修状況などで科目を絞り込めます。",
        side: "bottom",
        align: "end",
      },
    },
    {
      element: "#tutorial-course-list",
      popover: {
        title: "科目一覧",
        description:
          "カードをクリックすると詳細情報が表示され、科目名をクリックするとシラバスを確認できます。科目の登録・解除を行うと時間割ページに反映されます。",
        side: "top",
        align: "center",
      },
    },
  ],
  timetable: [
    {
      element: "#tutorial-tabs",
      popover: {
        title: "前期 / 後期",
        description: "タブで前期・後期を切り替えて時間割を確認できます。",
        side: "bottom",
        align: "start",
      },
    },
    {
      element: "#tutorial-grid",
      popover: {
        title: "時間割表",
        description:
          "空欄のコマをクリックして科目を追加できます。登録済みの科目をクリックすると詳細表示・登録解除が可能です。",
        side: "bottom",
        align: "center",
      },
    },
    {
      element: "#tutorial-credits",
      popover: {
        title: "単位集計",
        description: "登録した科目の単位数が自動で集計されます。",
        side: "top",
        align: "center",
      },
    },
  ],
}

// ─── localStorage キー ────────────────────────────────────────────────────────

const tourKey = (page: string) => `TIME_TUTORIAL_${page}`

// ─── Context ─────────────────────────────────────────────────────────────────

interface TutorialContextType {
  startTour: (page: string) => void
  resetAndStartTour: (page: string) => void
}

const TutorialContext = createContext<TutorialContextType | undefined>(
  undefined
)

// ─── Provider ────────────────────────────────────────────────────────────────

export function TutorialProvider({ children }: { children: ReactNode }) {
  // driver インスタンスをキャッシュ (生成コスト削減)
  const driverRef = useRef<ReturnType<
    (typeof import("driver.js"))["driver"]
  > | null>(null)

  const launchTour = useCallback(async (page: string) => {
    const steps = TOURS[page]
    if (!steps) return

    // ステップ内の要素が DOM に存在するか確認
    const firstEl = document.querySelector(steps[0].element as string)
    if (!firstEl) return

    // driver.js を動的 import (コード分割)
    const { driver } = await import("driver.js")
    await import("driver.js/dist/driver.css")

    driverRef.current?.destroy()

    driverRef.current = driver({
      showProgress: true,
      nextBtnText: "次へ",
      prevBtnText: "戻る",
      doneBtnText: "完了",
      steps,
      onDestroyStarted: () => {
        localStorage.setItem(tourKey(page), "done")
        driverRef.current?.destroy()
      },
    })

    driverRef.current.drive()
  }, [])

  const startTour = useCallback(
    (page: string) => {
      const done = localStorage.getItem(tourKey(page))
      if (done) return
      launchTour(page)
    },
    [launchTour]
  )

  const resetAndStartTour = useCallback(
    (page: string) => {
      localStorage.removeItem(tourKey(page))
      launchTour(page)
    },
    [launchTour]
  )

  return (
    <TutorialContext.Provider value={{ startTour, resetAndStartTour }}>
      {children}
    </TutorialContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useTutorial() {
  const context = useContext(TutorialContext)
  if (!context) {
    throw new Error("useTutorial must be used within TutorialProvider")
  }
  return context
}
