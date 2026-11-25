import { useQuery } from '@tanstack/react-query'
import { CalendarClock } from 'lucide-react'
import { api } from '../../api/client.js'
import { formatDay } from '../../lib/format.js'

const WORDS = { ok: 'OK', due_soon: 'Due soon', overdue: 'Overdue' }
const STYLES = { ok: 'bg-brand-soft text-brand-dark', due_soon: 'bg-amber-50 text-near', overdue: 'bg-red-50 text-bad' }

// When each piece of equipment is next due: 6 months after its latest service record.
export default function ServiceDue() {
  const { data } = useQuery({ queryKey: ['service-due'], queryFn: () => api('/service-records/due/') })
  if (!data?.length) return null
  return (
    <section className="mt-4 rounded-xl border border-line bg-surface p-4" aria-label="Next services due">
      <h2 className="flex items-center gap-2 font-semibold">
        <CalendarClock size={18} aria-hidden="true" /> Next service due (every 6 months)
      </h2>
      <ul className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {data.map((item) => (
          <li key={item.equipment} className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2 text-sm">
            <span>
              <span className="font-semibold">{item.equipment}</span>
              <br />
              <span className="text-muted">Due {formatDay(item.due)} · last {formatDay(item.last_service)}</span>
            </span>
            <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold ${STYLES[item.state]}`}>
              {WORDS[item.state]}{item.state !== 'ok' && ` · ${item.days_left < 0 ? `${-item.days_left}d late` : `${item.days_left}d`}`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
