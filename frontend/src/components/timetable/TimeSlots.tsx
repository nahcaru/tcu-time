import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table"

const SLOTS = [
  { id: 1, text: "9:20-11:00" },
  { id: 2, text: "11:10-12:50" },
  { id: 3, text: "13:40-15:20" },
  { id: 4, text: "15:30-17:10" },
  { id: 5, text: "17:20-19:00" },
]

export function TimeSlots() {
  return (
    <div className="overflow-x-auto rounded-md border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            {SLOTS.map((slot) => (
              <TableHead
                key={slot.id}
                className="px-4 py-3 text-center whitespace-nowrap"
              >
                {slot.id}時限{" "}
                <span className="ml-1 text-xs text-muted-foreground">
                  {slot.text}
                </span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
      </Table>
    </div>
  )
}
