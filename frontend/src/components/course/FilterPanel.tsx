import { IconFilter } from "@tabler/icons-react"
import { useIsMobile } from "@/hooks/use-mobile"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { TERMS, TARGETS } from "@/lib/constants"

interface FilterPanelProps {
  selectedTargets: string[]
  selectedTerms: string[]
  enrolledOnly: boolean
  freeSlotsOnly: boolean
  advanceEnrollmentOnly: boolean
  onTargetsChange: (targets: string[]) => void
  onTermsChange: (terms: string[]) => void
  onEnrolledOnlyChange: (enrolled: boolean) => void
  onFreeSlotsOnlyChange: (freeSlotsOnly: boolean) => void
  onAdvanceEnrollmentOnlyChange: (advanceEnrollment: boolean) => void
}

function FilterContent({
  selectedTargets,
  selectedTerms,
  enrolledOnly,
  freeSlotsOnly,
  advanceEnrollmentOnly,
  onTargetsChange,
  onTermsChange,
  onEnrolledOnlyChange,
  onFreeSlotsOnlyChange,
  onAdvanceEnrollmentOnlyChange,
}: FilterPanelProps) {
  const toggleTarget = (code: string) => {
    if (selectedTargets.includes(code)) {
      onTargetsChange(selectedTargets.filter((c) => c !== code))
    } else {
      onTargetsChange([...selectedTargets, code])
    }
  }

  const toggleTerm = (term: string) => {
    if (selectedTerms.includes(term)) {
      onTermsChange(selectedTerms.filter((t) => t !== term))
    } else {
      onTermsChange([...selectedTerms, term])
    }
  }

  const handleSelectAllTargets = () => {
    onTargetsChange(TARGETS.map(t => t.code))
  }

  const handleClearTargets = () => {
    onTargetsChange([])
  }

  return (
    <div className="flex flex-col gap-6 py-4">
      {/* 登録済み & 空きコマ */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="registered"
            checked={enrolledOnly}
            onCheckedChange={(checked) =>
              onEnrolledOnlyChange(checked === true)
            }
          />
          <label
            htmlFor="registered"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            登録済み
          </label>
        </div>
        
        <div className="flex items-center space-x-2">
          <Checkbox
            id="freeslots"
            checked={freeSlotsOnly}
            onCheckedChange={(checked) =>
              onFreeSlotsOnlyChange(checked === true)
            }
          />
          <label
            htmlFor="freeslots"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            空きコマのみ
          </label>
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="advance"
            checked={advanceEnrollmentOnly}
            onCheckedChange={(checked) =>
              onAdvanceEnrollmentOnlyChange(checked === true)
            }
          />
          <label
            htmlFor="advance"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            先行履修可
          </label>
        </div>
      </div>

      {/* 学期 */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold">学期</h4>
        <div className="grid grid-cols-2 gap-3">
          {TERMS.map((term) => (
            <div key={term} className="flex items-center space-x-2">
              <Checkbox
                id={`term-${term}`}
                checked={selectedTerms.includes(term)}
                onCheckedChange={() => toggleTerm(term)}
              />
              <label htmlFor={`term-${term}`} className="text-sm">
                {term}
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* 対象 */}
      <div className="space-y-2 pb-6">
        <div className="flex items-center justify-between pb-1">
          <h4 className="text-sm font-semibold">対象</h4>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
              onClick={handleSelectAllTargets}
            >
              全選択
            </Button>
            <span className="text-muted-foreground text-xs">/</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
              onClick={handleClearTargets}
            >
              クリア
            </Button>
          </div>
        </div>
        <div className="flex flex-col gap-3">
          {TARGETS.map((target) => (
            <div key={target.code} className="flex items-center space-x-2">
              <Checkbox
                id={`target-${target.code}`}
                checked={selectedTargets.includes(target.code)}
                onCheckedChange={() => toggleTarget(target.code)}
              />
              <label
                htmlFor={`target-${target.code}`}
                className="text-sm line-clamp-1"
                title={target.label}
              >
                {target.label}
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function FilterPanel(props: FilterPanelProps) {
  const isMobile = useIsMobile()

  if (isMobile) {
    return (
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline" size="icon" className="shrink-0">
            <IconFilter className="h-4 w-4" />
            <span className="sr-only">フィルター</span>
          </Button>
        </SheetTrigger>
        <SheetContent
          side="bottom"
          className="h-[85vh] overflow-y-auto w-full"
        >
          <SheetHeader className="text-left">
            <SheetTitle>絞り込み</SheetTitle>
          </SheetHeader>
          <FilterContent {...props} />
        </SheetContent>
      </Sheet>
    )
  }

  return (
    <div className="w-[200px] shrink-0 border-r pr-6 hidden lg:block h-full overflow-y-auto no-scrollbar">
      <h3 className="font-semibold mb-2">絞り込み</h3>
      <FilterContent {...props} />
    </div>
  )
}
