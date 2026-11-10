import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, XOctagon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { formatDay } from '../lib/format.js'

// Monthly and quarterly cleaning tasks that are due or overdue (forklift, pest spray, bait change).
// `enabled` is false for the night login, which may not see the Cleaning module.
export function useCleaningNotifications(enabled = true) {
  return useQuery({
    queryKey: ['cleaning-notifications'],
    queryFn: () => api('/cleaning-checks/notifications/'),
    refetchInterval: 60_000,
    enabled,
  })
}

// The words for one due task. Shape and words as well as colour, so it never depends on colour alone.
export function dueText(item) {
  const since = formatDay(item.due_date)
  return item.state === 'overdue'
    ? `${item.name} is OVERDUE. It was due on ${since}.`
    : `${item.name} is due (since ${since}).`
}

// One banner for each task that is due. Shown on the front page and the Cleaning home.
export default function CleaningNotices({ enabled = true }) {
  const { data } = useCleaningNotifications(enabled)
  if (!data || data.due.length === 0) return null
  return (
    <div className="space-y-2">
      {data.due.map((item) => {
        const overdue = item.state === 'overdue'
        const Icon = overdue ? XOctagon : AlertTriangle
        return (
          <div
            key={item.task}
            role="status"
            className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${
              overdue ? 'border-bad/50 bg-red-50 text-bad' : 'border-near/50 bg-amber-50 text-near'
            }`}
          >
            <p className="flex items-center gap-2 font-medium">
              <Icon size={20} aria-hidden="true" /> {dueText(item)}
            </p>
            <Link to="/cleaning" className="inline-flex h-10 items-center rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-dark">
              Tick it off
            </Link>
          </div>
        )
      })}
    </div>
  )
}

// The little count beside "Notifications" in the Cleaning menu.
export function CleaningNavBadge() {
  const { data } = useCleaningNotifications()
  if (!data || data.count === 0) return null
  return (
    <span className="ml-auto rounded-full bg-bad px-2 py-0.5 text-xs font-semibold text-white" aria-label={`${data.count} due`}>
      {data.count}
    </span>
  )
}
