/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  type ReactNode,
} from "react"

interface ScrollContextType {
  headerVisible: boolean
  scrollRootRef: React.RefObject<HTMLDivElement | null>
}

const ScrollContext = createContext<ScrollContextType | undefined>(undefined)

export function ScrollProvider({ children }: { children: ReactNode }) {
  const [headerVisible, setHeaderVisible] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)
  const scrollRootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const scrollNode = scrollRootRef.current
    if (!scrollNode) return

    const handleScroll = () => {
      const currentScrollY = scrollNode.scrollTop

      if (currentScrollY < 50) {
        setHeaderVisible(true)
      } else if (currentScrollY > lastScrollY + 5) {
        setHeaderVisible(false)
      } else if (currentScrollY < lastScrollY - 5) {
        setHeaderVisible(true)
      }

      setLastScrollY(currentScrollY)
    }

    scrollNode.addEventListener("scroll", handleScroll, { passive: true })
    return () => scrollNode.removeEventListener("scroll", handleScroll)
  }, [lastScrollY])

  return (
    <ScrollContext.Provider value={{ headerVisible, scrollRootRef }}>
      {children}
    </ScrollContext.Provider>
  )
}

export function useScroll() {
  const context = useContext(ScrollContext)
  if (context === undefined) {
    throw new Error("useScroll must be used within a ScrollProvider")
  }
  return context
}
