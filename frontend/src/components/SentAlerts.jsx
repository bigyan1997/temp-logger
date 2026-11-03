import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client.js'
import { formatDateTime } from '../lib/format.js'

// The alert emails already sent (the last 100), so you can check a reminder went out.
export default function SentAlerts() {
  const { data: alerts = [], isLoading } = useQuery({ queryKey: ['alerts-sent'], queryFn: () => api('/alerts-sent/') })

  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold">Sent alerts</h2>
      <p className="mt-1 text-muted">Emails already sent, newest first. Each alert is sent only once.</p>

      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[480px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Sent</th>
              <th className="px-4 py-3 font-medium">Alert</th>
              <th className="px-4 py-3 font-medium">Reading time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={3} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && alerts.length === 0 && <tr><td colSpan={3} className="px-4 py-3 text-muted">No alerts have been sent yet.</td></tr>}
            {alerts.map((a) => (
              <tr key={a.id}>
                <td className="whitespace-nowrap px-4 py-3 text-sm">{formatDateTime(a.sent_at)}</td>
                <td className="px-4 py-3">{a.what}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-muted">{a.reading_time ? formatDateTime(a.reading_time) : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
