import { Input } from "@/components/ui/input"
import { IconSearch } from "@tabler/icons-react"

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="relative w-full max-w-[300px]">
      <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder="科目名・担当者で検索"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-9 h-10"
      />
    </div>
  )
}
