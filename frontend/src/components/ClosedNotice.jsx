import { CalendarOff } from 'lucide-react'

// A note on a day that is closed (a public holiday). Readings can still be logged underneath it.
export default function ClosedNotice({ label, children }) {
  return (
    <p role="status" className="mb-4 flex items-start gap-2 rounded-xl border border-line bg-brand-soft px-4 py-3 text-sm">
      <CalendarOff size={18} className="mt-0.5 shrink-0 text-brand" aria-hidden="true" />
      <span>
        <strong>{label}.</strong> {children}
      </span>
    </p>
  )
}
