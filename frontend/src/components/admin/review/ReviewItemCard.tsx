import { useState, useRef, useEffect, type ReactNode } from "react"
import { Card } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { IconChevronDown, IconChevronUp, IconTrash } from "@tabler/icons-react"

interface ReviewItemCardProps {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  title: string
  subtitle?: string
  badges?: ReactNode
  children: ReactNode
  onRemove?: () => void
  className?: string
  isActive?: boolean
  onClickHeader?: () => void
  isOpen?: boolean
  onToggleOpen?: () => void
}

export function ReviewItemCard({
  checked,
  onCheckedChange,
  title,
  subtitle,
  badges,
  children,
  onRemove,
  className,
  isActive = false,
  onClickHeader,
  isOpen: controlledIsOpen,
  onToggleOpen,
}: ReviewItemCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [internalIsOpen, setInternalIsOpen] = useState(!checked)
  const [prevChecked, setPrevChecked] = useState(checked)

  if (checked !== prevChecked) {
    setPrevChecked(checked)
    setInternalIsOpen(!checked)
  }

  const isExpanded =
    controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen

  const handleToggle = () => {
    if (onClickHeader) onClickHeader()
    if (onToggleOpen) {
      onToggleOpen()
    } else {
      setInternalIsOpen(!internalIsOpen)
    }
  }

  useEffect(() => {
    if (isActive && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" })
    }
  }, [isActive])

  return (
    <Card
      ref={cardRef}
      className={cn(
        "gap-0 overflow-hidden rounded-xl border py-0 shadow-xs transition-all",
        isActive && "ring-2 ring-primary ring-offset-2 ring-offset-background",
        checked
          ? "border-border/60 bg-card/60"
          : "border-border bg-card ring-1 ring-primary/20",
        className
      )}
    >
      {/* Toggle header containing checkbox, title, tags, and chevron */}
      <div
        className={cn(
          "flex cursor-pointer items-center gap-3 p-3 text-left transition-colors select-none hover:bg-muted/40 sm:px-4",
          isExpanded && "border-b bg-muted/20"
        )}
        onClick={handleToggle}
      >
        {/* Checkbox placed inside the toggle header */}
        <div
          onClick={(e) => e.stopPropagation()}
          className="flex shrink-0 items-center"
        >
          <Checkbox
            checked={checked}
            onCheckedChange={(c) => onCheckedChange(c === true)}
            aria-label={title}
          />
        </div>

        {/* Title, tags, and subtitle */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center gap-2">
            <span className="truncate text-sm font-semibold">{title}</span>
            {badges}
          </div>
          {subtitle && (
            <span className="truncate text-xs text-muted-foreground">
              {subtitle}
            </span>
          )}
        </div>

        {/* Action buttons and expand/collapse chevron */}
        <div className="flex shrink-0 items-center gap-1">
          {onRemove && (
            <div onClick={(e) => e.stopPropagation()}>
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                onClick={onRemove}
                className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                title="項目を削除"
              >
                <IconTrash className="size-3.5" />
              </Button>
            </div>
          )}
          <div className="p-1 text-muted-foreground">
            {isExpanded ? (
              <IconChevronUp className="size-4" />
            ) : (
              <IconChevronDown className="size-4" />
            )}
          </div>
        </div>
      </div>

      {/* Expandable content area */}
      {isExpanded && (
        <div className="space-y-4 bg-card/50 p-3 sm:p-4">{children}</div>
      )}
    </Card>
  )
}
