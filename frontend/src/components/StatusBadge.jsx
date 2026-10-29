import { AlertTriangle, CheckCircle2, Circle, XOctagon } from 'lucide-react'

// Every status has a colour, a different shape AND words, so it never depends on colour alone.
const statuses = {
  ok: { label: 'In range', Icon: CheckCircle2, className: 'bg-green-50 text-ok' },
  near_limit: { label: 'Near limit', Icon: AlertTriangle, className: 'bg-amber-50 text-near' },
  out_of_limit: { label: 'Out of limit', Icon: XOctagon, className: 'bg-red-50 text-bad' },
  none: { label: 'Not logged', Icon: Circle, className: 'bg-bg text-muted' },
}

export default function StatusBadge({ status = 'none' }) {
  const { label, Icon, className } = statuses[status] ?? statuses.none
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-sm font-medium ${className}`}>
      <Icon size={14} aria-hidden="true" /> {label}
    </span>
  )
}
