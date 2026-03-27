/**
 * usePageTutorial
 *
 * 指定ページの初回訪問時チュートリアルを自動起動する hook。
 * ページコンポーネントの最上部で usePageTutorial("courses") のように呼ぶ。
 *
 * use-tutorial.tsx と分離することで Fast Refresh の警告を回避する。
 */
import { useEffect } from "react"
import { useLocation } from "react-router"
import { useTutorial } from "./use-tutorial"

export function usePageTutorial(page: string) {
  const { startTour } = useTutorial()
  const location = useLocation()

  useEffect(() => {
    // DOM が描画された後に起動するため、少し遅延させる
    const timer = setTimeout(() => {
      startTour(page)
    }, 600)

    return () => clearTimeout(timer)
    // location.pathname が変わるたびに再評価 (SPA遷移対応)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])
}
