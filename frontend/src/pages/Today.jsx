import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { formatLongDate, formatTime, todayInSydney } from '../lib/format.js'
import { useDay } from '../lib/useDay.js'

function Card({ title, to, children }) {
  return (
    <section className="rounded-xl border border-line bg-surface">
      <h2 className="border-b border-line px-4 py-3 font-semibold">{title}</h2>
      <div className="px-4 py-3">{children}</div>
      <Link
        to={to}
        className="flex items-center justify-between border-t border-line px-4 py-3 font-medium text-brand hover:bg-brand-soft"
      >
        Log {title.toLowerCase()} <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </section>
  )
}

const stateText = { done: 'Done', due: 'Due now', missed: 'Missed', upcoming: 'Not due yet' }
const stateStatus = { done: 'ok', due: 'near_limit', missed: 'out_of_limit', upcoming: 'none' }

// Night staff's home: what has to be logged today, and how far along it is.
export default function Today() {
  const { user } = useAuth()
  const { data: day } = useDay(todayInSydney())

  const logged = (items, field) => items.filter((item) => item[field]).length

  return (
    <div className="max-w-5xl">
      <h1 className="text-2xl font-semibold">Hello, {user.display_name}</h1>
      <p className="text-muted">{formatLongDate()}</p>

      {!day ? (
        <p className="mt-6 text-muted">Loading…</p>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <Card title="Storage" to="/log/storage">
            {day.storage.length === 0 && <p className="text-muted">No readings scheduled today.</p>}
            <ul className="grid gap-2">
              {day.storage.map((slot) => (
                <li key={slot.slot} className="flex items-center justify-between gap-2">
                  <span>
                    <span className="font-medium">{formatTime(slot.slot)}</span>
                    <span className="text-muted"> · {logged(slot.units, 'reading')} of {slot.units.length} units</span>
                  </span>
                  <span title={stateText[slot.state]}>
                    <StatusBadge status={stateStatus[slot.state]} />
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Receiving" to="/log/receiving">
            <p className="text-3xl font-semibold tabular-nums">
              {logged(day.receiving, 'entry')}
              <span className="text-lg text-muted"> of {day.receiving.length} suppliers</span>
            </p>
          </Card>

          <Card title="Dispatch" to="/log/dispatch">
            <p className="text-3xl font-semibold tabular-nums">
              {logged(day.dispatch, 'entry')}
              <span className="text-lg text-muted"> of {day.dispatch.length} runs</span>
            </p>
          </Card>
        </div>
      )}
    </div>
  )
}
