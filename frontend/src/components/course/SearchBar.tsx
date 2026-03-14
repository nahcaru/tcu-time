import { Input } from "@/components/ui/input"
import { IconSearch } from "@tabler/icons-react"

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="relative w-full">
      <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        placeholder="科目名・担当者で検索"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 pl-9"
      />
    </div>
  )
}
