import { AlertTriangle, CheckCircle2 } from 'lucide-react'

// The first thing on the dashboard: is everything fine, or what needs doing?
// `items` is a list of { label, count }. Only the ones with something to do are shown.
export default function StatusBanner({ items, loggedToday }) {
  const todo = items.filter((item) => item.count > 0)
  const allClear = todo.length === 0

  return (
    <div
      role="status"
      className={`flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border p-5 ${
        allClear ? 'border-ok/40 bg-green-50' : 'border-near/50 bg-amber-50'
      }`}
    >
      {allClear ? (
        <CheckCircle2 size={32} className="text-ok" aria-hidden="true" />
      ) : (
        <AlertTriangle size={32} className="text-near" aria-hidden="true" />
      )}

      <div className="min-w-0 flex-1">
        <p className="text-xl font-semibold">{allClear ? 'All clear' : 'Needs attention'}</p>
        <p className="text-sm text-muted">
          {allClear ? 'Every reading is logged and nothing is waiting for sign-off.' : 'Work through these below.'}
        </p>
      </div>

      <ul className="flex flex-wrap gap-3">
        {todo.map((item) => (
          <li key={item.label} className="rounded-lg border border-near/40 bg-surface px-4 py-2 text-center">
            <p className="text-2xl font-semibold tabular-nums text-near">{item.count}</p>
            <p className="text-xs font-medium text-muted">{item.label}</p>
          </li>
        ))}
        <li className="rounded-lg border border-line bg-surface px-4 py-2 text-center">
          <p className="text-2xl font-semibold tabular-nums">{loggedToday}</p>
          <p className="text-xs font-medium text-muted">Logged today</p>
        </li>
      </ul>
    </div>
  )
}
