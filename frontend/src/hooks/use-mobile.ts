import { useEffect, useState } from "react"

const MOBILE_BREAKPOINT = 1024

/**
 * レスポンシブ判定 hook
 *
 * Returns true when viewport width < 1024px (mobile).
 * Used to switch between Sidebar (desktop) and BottomNav (mobile).
 */
export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches)

    setIsMobile(mql.matches)
    mql.addEventListener("change", onChange)

    return () => mql.removeEventListener("change", onChange)
  }, [])

  return isMobile
}
