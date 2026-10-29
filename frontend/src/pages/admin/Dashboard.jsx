import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { api } from '../../api/client.js'
import StaffPicker, { useStaffChoice } from '../../components/StaffPicker.jsx'
import StatTile from '../../components/StatTile.jsx'
import { formatDateTime, formatLongDate } from '../../lib/format.js'

const REFRESH_EVERY_MS = 60_000

function Panel({ title, count, children }) {
  return (
    <section className="rounded-xl border border-line bg-surface">
      <h2 className="flex items-center justify-between border-b border-line px-4 py-3 font-semibold">
        {title}
        {count > 0 && <span className="rounded-full bg-brand-soft px-2 text-sm text-brand-dark">{count}</span>}
      </h2>
      {children}
    </section>
  )
}

function AllClear({ children }) {
  return (
    <p className="flex items-center gap-2 px-4 py-4 text-ok">
      <CheckCircle2 size={18} aria-hidden="true" /> {children}
    </p>
  )
}

export default function Dashboard() {
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api('/dashboard/'),
    refetchInterval: REFRESH_EVERY_MS,
  })
  const { data: waiting } = useQuery({
    queryKey: ['unsigned-actions'],
    queryFn: () => api('/corrective-actions/?unsigned=1'),
    refetchInterval: REFRESH_EVERY_MS,
  })

  const { staff, staffId, setStaffId } = useStaffChoice() // the sign-off login is shared, so ask who is signing

  const signOff = useMutation({
    mutationFn: (id) => api(`/corrective-actions/${id}/signoff/`, { method: 'POST', body: { staff: Number(staffId) } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['unsigned-actions'] })
    },
  })

  const tiles = data?.tiles
  const actions = waiting?.results ?? []

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
        <Panel title="Waiting for sign-off" count={actions.length}>
          {actions.length === 0 && <AllClear>Nothing to sign off.</AllClear>}
          {actions.length > 0 && (
            <div className="border-b border-line px-4 pt-3">
              <StaffPicker staff={staff} staffId={staffId} setStaffId={setStaffId} />
            </div>
          )}
          {signOff.isError && (
            <p role="alert" className="px-4 pt-3 text-sm text-bad">
              {signOff.error.message}
            </p>
          )}
          <ul className="divide-y divide-line">
            {actions.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{a.summary}</p>
                  <p className="truncate text-sm text-muted">
                    {a.action_label} · {formatDateTime(a.created_at)} · Logged by {a.logged_by_name}
                    {a.notes && ` · ${a.notes}`}
                  </p>
                </div>
                <button
                  onClick={() => signOff.mutate(a.id)}
                  disabled={signOff.isPending || !staffId}
                  title={staffId ? undefined : 'Choose your name first'}
                  className="h-10 shrink-0 rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
                >
                  Sign off
                </button>
              </li>
            ))}
          </ul>
        </Panel>

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
