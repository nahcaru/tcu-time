import { IconFilter } from "@tabler/icons-react"
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { TARGETS, SPRING_TERMS, FALL_TERMS } from "@/lib/constants"

interface FilterPanelProps {
  id?: string
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

export function FilterContent({
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
    onTargetsChange(TARGETS.map((t) => t.code))
  }

  const handleClearTargets = () => {
    onTargetsChange([])
  }

  const handleSelectAllSpring = () => {
    onTermsChange([...new Set([...selectedTerms, ...SPRING_TERMS])])
  }

  const handleClearSpring = () => {
    onTermsChange(
      selectedTerms.filter(
        (term) => !(SPRING_TERMS as readonly string[]).includes(term)
      )
    )
  }

  const handleSelectAllFall = () => {
    onTermsChange([...new Set([...selectedTerms, ...FALL_TERMS])])
  }

  const handleClearFall = () => {
    onTermsChange(
      selectedTerms.filter(
        (term) => !(FALL_TERMS as readonly string[]).includes(term)
      )
    )
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
            className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
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
            className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            空きコマ
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
            className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            先行履修可
          </label>
        </div>
      </div>

      {/* 学期 */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold">学期</h4>

        {/* 前期系 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between py-1">
            <h5 className="text-xs font-medium">前期開講</h5>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                onClick={handleSelectAllSpring}
              >
                全選択
              </Button>
              <span className="text-xs text-muted-foreground">/</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                onClick={handleClearSpring}
              >
                クリア
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {SPRING_TERMS.map((term) => (
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

        {/* 後期系 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between py-1">
            <h5 className="text-xs font-medium">後期開講</h5>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                onClick={handleSelectAllFall}
              >
                全選択
              </Button>
              <span className="text-xs text-muted-foreground">/</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                onClick={handleClearFall}
              >
                クリア
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {FALL_TERMS.map((term) => (
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

        <div className="space-y-2">
          <h5 className="py-1 text-xs font-medium">その他</h5>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="term-通年"
                checked={selectedTerms.includes("通年")}
                onCheckedChange={() => toggleTerm("通年")}
              />
              <label htmlFor="term-通年" className="text-sm">
                通年
              </label>
            </div>
          </div>
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
            <span className="text-xs text-muted-foreground">/</span>
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
                className="line-clamp-1 text-sm"
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
  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="shrink-0"
          id={props.id}
        >
          <IconFilter className="h-4 w-4" />
          <span className="sr-only">フィルター</span>
        </Button>
      </DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>フィルター</DrawerTitle>
        </DrawerHeader>
        <div className="no-scrollbar overflow-y-auto px-4">
          <FilterContent {...props} />
        </div>
      </DrawerContent>
    </Drawer>
  )
}
