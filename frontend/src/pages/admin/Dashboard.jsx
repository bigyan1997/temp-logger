import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client.js'
import { AllClear, Panel } from '../../components/Panel.jsx'
import SignOffPanel from '../../components/SignOffPanel.jsx'
import StatTile from '../../components/StatTile.jsx'
import { formatDateTime, formatLongDate } from '../../lib/format.js'

const REFRESH_EVERY_MS = 60_000

export default function Dashboard() {
  const { data } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api('/dashboard/'),
    refetchInterval: REFRESH_EVERY_MS,
  })

  const tiles = data?.tiles

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="text-muted">{formatLongDate()}</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Missed readings" value={tiles?.missed ?? 0} attention note="Not logged in time" />
        <StatTile label="Out of limit (7 days)" value={tiles?.out_of_limit ?? 0} attention note="Check these below" />
        <StatTile
          label="Waiting for sign-off"
          value={tiles?.awaiting_signoff ?? 0}
          attention
          tone="warn"
          note="Corrective actions to review"
        />
        <StatTile label="Logged today" value={tiles?.logged_today ?? 0} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <SignOffPanel />

        <Panel title="Missed readings" count={data?.missed.length}>
          {data?.missed.length === 0 && <AllClear>Every reading is logged.</AllClear>}
          <ul className="divide-y divide-line">
            {data?.missed.map((m) => (
              <li key={`${m.unit}-${m.slot}`} className="px-4 py-3">
                <span className="font-medium">{m.unit}</span>
                <span className="text-muted"> · due {formatDateTime(m.slot)}</span>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Out of limit in the last 7 days" count={data?.out_of_limit.length}>
          {data?.out_of_limit.length === 0 && <AllClear>No out-of-limit readings.</AllClear>}
          <ul className="divide-y divide-line">
            {data?.out_of_limit.map((r) => (
              <li key={`${r.kind}-${r.recorded_at}-${r.summary}`} className="px-4 py-3">
                <p className="font-medium">{r.summary}</p>
                <p className="text-sm text-muted">
                  {r.action} · {r.recorded_by} · {formatDateTime(r.recorded_at)} ·{' '}
                  {r.signed_off ? 'Signed off' : 'Not signed off yet'}
                </p>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  )
}
