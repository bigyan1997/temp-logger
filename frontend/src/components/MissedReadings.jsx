import { AlertTriangle } from 'lucide-react'
import { formatDateTime } from '../lib/format.js'

// A reminder at the top of the storage screen for readings that were never logged,
// with a button that opens that day and time so they can be entered now.
export default function MissedReadings({ missed, onLog }) {
  if (!missed?.length) return null

  return (
    <section aria-label="Missed readings" className="mb-4 rounded-xl border border-bad/50 bg-red-50 p-4">
      <h2 className="flex items-center gap-2 font-semibold text-bad">
        <AlertTriangle size={18} aria-hidden="true" /> Missed readings to log
      </h2>
      <ul className="mt-2 divide-y divide-bad/20">
        {missed.map((group) => (
          <li key={group.slot} className="flex flex-wrap items-center justify-between gap-3 py-2">
            <p>
              <span className="font-medium">{formatDateTime(group.slot)}</span>
              <span className="text-muted"> · not logged: {group.units.join(', ')}</span>
            </p>
            <button
              onClick={() => onLog(group)}
              className="h-10 rounded-lg bg-bad px-4 text-sm font-semibold text-white hover:opacity-90"
            >
              Log these now
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
