import { PERIOD_TIMES, PERIOD_TIMES_NUCLEAR } from "@/lib/constants"
import { useSettings } from "@/hooks/use-settings"
import { Table, TableBody, TableRow, TableCell } from "@/components/ui/table"

export function TimeSlots() {
  const { settings } = useSettings()
  const isNuclear = settings?.department === "06"
  const times = isNuclear ? PERIOD_TIMES_NUCLEAR : PERIOD_TIMES

  const slots = Object.entries(times).map(([id, text]) => ({
    id: parseInt(id),
    text,
  }))

  return (
    <div className="overflow-hidden rounded-md border bg-card">
      <Table>
        <TableBody>
          <TableRow className="flex flex-col divide-y divide-border hover:bg-transparent md:table-row md:divide-x md:divide-y-0">
            {slots.map((slot) => (
              <TableCell
                key={slot.id}
                className="flex items-center justify-between px-4 py-1.5 text-foreground md:table-cell md:px-2 md:text-center"
              >
                <div className="text-xs font-semibold md:text-sm">
                  {slot.id}時限
                </div>
                <div className="font-mono text-[11px] text-muted-foreground md:mt-0.5 md:text-xs">
                  {slot.text}
                </div>
              </TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>
    </div>
  )
}
