import * as React from "react"
import { useState, useRef, useEffect } from "react"
import { InputGroup, InputGroupAddon } from "@/components/ui/input-group"
import { IconSearch, IconX } from "@tabler/icons-react"
import { Command as CommandPrimitive } from "cmdk"
import {
  Command,
  CommandItem,
  CommandList,
  CommandGroup,
} from "@/components/ui/command"

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  suggestions?: string[]
}

export function SearchBar({
  value,
  onChange,
  suggestions = [],
}: SearchBarProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [hasNavigated, setHasNavigated] = useState(false)

  // クリックアウトサイドでドロップダウンを閉じる
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  // 入力が一致する候補をフィルタリング
  const filteredSuggestions = React.useMemo(() => {
    if (!value.trim()) return []
    const q = value.toLowerCase()
    return suggestions.filter((s) => s.toLowerCase().includes(q)).slice(0, 10)
  }, [suggestions, value])

  const handleClear = () => {
    onChange("")
    inputRef.current?.focus()
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-sm">
      <Command
        shouldFilter={false}
        className="overflow-visible bg-transparent p-0"
      >
        <InputGroup className="w-full">
          <CommandPrimitive.Input
            ref={inputRef}
            data-slot="input-group-control"
            placeholder="科目名・担当者で検索"
            value={value}
            onValueChange={(v) => {
              onChange(v)
              setOpen(true)
              setHasNavigated(false)
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                setHasNavigated(true)
              }
              if (e.key === "Enter" && !hasNavigated) {
                setOpen(false)
                e.preventDefault()
              }
              if (e.key === "Escape") {
                setOpen(false)
              }
            }}
            className="flex-1 rounded-none border-0 bg-transparent px-2.5 py-1 text-sm shadow-none ring-0 outline-none focus-visible:ring-0 aria-invalid:ring-0 dark:bg-transparent"
          />
          <InputGroupAddon>
            <IconSearch />
          </InputGroupAddon>
          {value && (
            <InputGroupAddon
              align="inline-end"
              onClick={handleClear}
              className="cursor-pointer transition-colors hover:text-foreground"
            >
              <IconX />
            </InputGroupAddon>
          )}
        </InputGroup>

        {open && value && filteredSuggestions.length > 0 && (
          <div className="absolute top-full right-0 left-0 z-50 mt-1 max-h-[300px] animate-in overflow-y-auto rounded-md border bg-popover text-popover-foreground shadow-md fade-in-0 zoom-in-95">
            <CommandList className="py-1">
              <CommandGroup heading="検索候補">
                {filteredSuggestions.map((s) => (
                  <CommandItem
                    key={s}
                    value={s}
                    onSelect={(v) => {
                      onChange(v)
                      setOpen(false)
                    }}
                    className="flex items-center gap-2"
                  >
                    <span>{s}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </div>
        )}
      </Command>
    </div>
  )
}
