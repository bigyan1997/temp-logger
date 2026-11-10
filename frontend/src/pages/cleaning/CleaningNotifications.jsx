import CalibrationStatus from '../../components/CalibrationStatus.jsx'
import CleaningNotices, { useCleaningNotifications } from '../../components/CleaningNotices.jsx'
import { formatDateTime } from '../../lib/format.js'

// What needs doing: monthly and quarterly cleaning tasks that are due, the thermometer calibration, and the
// reminder emails already sent. Day staff only.
export default function CleaningNotifications() {
  const { data, isLoading } = useCleaningNotifications()
  const sent = data?.sent ?? []

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold">Notifications</h1>
      <p className="mt-1 max-w-prose text-muted">
        A task shows here from the first working day of its month or quarter until it is ticked off, and is marked overdue after a week.
        Reminder emails go to the Alert emails list (Temperature Logger, Settings): once when it falls due, then once a week while it is not done.
        Choose which tasks send reminders on the Tasks page.
      </p>

      <h2 className="mb-2 mt-6 text-lg font-semibold">Due now</h2>
      <div className="space-y-2">
        {isLoading && <p className="text-muted">Loading…</p>}
        {data && data.due.length === 0 && <p className="rounded-xl border border-line bg-surface p-4 text-muted">Nothing is due. The monthly and quarterly tasks are up to date.</p>}
        <CleaningNotices />
        <CalibrationStatus />
      </div>

      <h2 className="mb-2 mt-8 text-lg font-semibold">Reminder emails sent</h2>
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[480px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Sent</th>
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Reminder</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {!isLoading && sent.length === 0 && <tr><td colSpan={3} className="px-4 py-3 text-muted">No reminder emails have been sent yet.</td></tr>}
            {sent.map((s) => (
              <tr key={s.id}>
                <td className="whitespace-nowrap px-4 py-3 text-sm">{formatDateTime(s.sent_at)}</td>
                <td className="px-4 py-3">{s.name}</td>
                <td className="px-4 py-3 text-muted">{s.what}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
