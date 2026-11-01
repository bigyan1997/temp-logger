import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Clock } from 'lucide-react'
import { api } from '../../api/client.js'
import { AllClear, Panel } from '../../components/Panel.jsx'
import SignOffPanel from '../../components/SignOffPanel.jsx'
import StatusBanner from '../../components/StatusBanner.jsx'
import TodayProgress from '../../components/TodayProgress.jsx'
import { formatDateTime, formatLongDate } from '../../lib/format.js'

const REFRESH_EVERY_MS = 60_000

export default function Dashboard() {
  const { data, isError, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api('/dashboard/'),
    refetchInterval: REFRESH_EVERY_MS,
  })

  const tiles = data?.tiles
  const banner = [
    { label: 'Missed readings', count: tiles?.missed ?? 0 },
    { label: 'Waiting for sign-off', count: tiles?.awaiting_signoff ?? 0 },
  ]

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="mb-5 text-muted">{formatLongDate()}</p>

      {isError && (
        <p role="alert" className="rounded-xl border border-bad/50 bg-red-50 p-4 text-bad">
          The dashboard could not load ({error.message}). It will try again in a minute, or refresh the page.
        </p>
      )}
      {!data && !isError && <p className="text-muted">Loading…</p>}

      {data && <StatusBanner items={banner} loggedToday={tiles.logged_today} />}

      {data?.today && (
        <div className="mt-6">
          <TodayProgress today={data.today} />
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <SignOffPanel />

        <Panel title="Missed readings" count={data?.missed.length}>
          {data?.missed.length === 0 && <AllClear>Every reading is logged.</AllClear>}
          <ul className="divide-y divide-line">
            {data?.missed.map((m) => (
              <li key={`${m.unit}-${m.slot}`} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="font-medium">{m.unit}</span>
                <span className="flex items-center gap-1 text-sm text-muted">
                  <Clock size={14} aria-hidden="true" /> due {formatDateTime(m.slot)}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="mt-6">
        <Panel title="Out of limit in the last 7 days" count={data?.out_of_limit.length}>
          {data?.out_of_limit.length === 0 && <AllClear>No out-of-limit readings.</AllClear>}
          {data?.out_of_limit.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-muted">
                  <tr className="border-b border-line">
                    <th className="px-4 py-2 font-medium">Reading</th>
                    <th className="px-4 py-2 font-medium">Action taken</th>
                    <th className="px-4 py-2 font-medium">Logged by</th>
                    <th className="px-4 py-2 font-medium">When</th>
                    <th className="px-4 py-2 font-medium">Sign-off</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.out_of_limit.map((r) => (
                    <tr key={`${r.kind}-${r.recorded_at}-${r.summary}`}>
                      <td className="px-4 py-3 font-medium">{r.summary}</td>
                      <td className="px-4 py-3">{r.action}</td>
                      <td className="px-4 py-3">{r.recorded_by}</td>
                      <td className="whitespace-nowrap px-4 py-3">{formatDateTime(r.recorded_at)}</td>
                      <td className="whitespace-nowrap px-4 py-3">
                        {r.signed_off ? (
                          <span className="flex items-center gap-1 text-ok">
                            <CheckCircle2 size={14} aria-hidden="true" /> Signed off
                          </span>
                        ) : (
                          <span className="text-near">Waiting</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
