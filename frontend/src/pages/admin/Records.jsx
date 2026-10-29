import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import VoidDialog from '../../components/VoidDialog.jsx'
import { formatDateTime, todayInSydney } from '../../lib/format.js'
import { formatTemp } from '../../lib/status.js'

// What differs between the three kinds of record.
const kinds = {
  storage: {
    label: 'Storage',
    endpoint: '/storage-readings/',
    valueField: 'value',
    what: (r) => `${r.unit_name} · ${formatDateTime(r.slot)}`,
    temp: (r) => formatTemp(r.value),
  },
  receiving: {
    label: 'Receiving',
    endpoint: '/receiving-checks/',
    valueField: 'temp',
    what: (r) => `${r.supplier_name} · ${r.date}`,
    temp: (r) => (r.no_delivery ? 'No delivery' : formatTemp(r.temp)),
  },
  dispatch: {
    label: 'Dispatch',
    endpoint: '/dispatch-readings/',
    valueField: 'temp',
    what: (r) => `Run ${r.run_code} · ${r.date}`,
    temp: (r) => formatTemp(r.temp),
  },
}

const daysAgo = (n) => {
  const d = new Date(todayInSydney())
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const inputClass = 'h-10 rounded-lg border border-line bg-surface px-3 focus:border-brand focus:outline-2 focus:outline-brand'

export default function Records() {
  const [kind, setKind] = useState('storage')
  const [from, setFrom] = useState(daysAgo(7))
  const [to, setTo] = useState(todayInSydney())
  const [onlyProblems, setOnlyProblems] = useState(false)
  const [showVoided, setShowVoided] = useState(false)
  const [voiding, setVoiding] = useState(null)
  const config = kinds[kind]

  const query = `?from=${from}&to=${to}${onlyProblems ? '&status=out_of_limit' : ''}${showVoided ? '&include_voided=1' : ''}`
  const { data, isLoading } = useQuery({
    queryKey: ['records', kind, from, to, onlyProblems, showVoided],
    queryFn: () => api(`${config.endpoint}${query}`),
  })
  const records = data?.results ?? []

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-semibold">Records</h1>

      <div className="mt-4 flex flex-wrap items-end gap-4">
        <div role="tablist" aria-label="Kind of record" className="flex gap-1">
          {Object.entries(kinds).map(([key, k]) => (
            <button
              key={key}
              role="tab"
              aria-selected={kind === key}
              onClick={() => setKind(key)}
              className={`h-10 rounded-lg px-4 font-medium ${kind === key ? 'bg-brand text-white' : 'border border-line bg-surface hover:bg-brand-soft'}`}
            >
              {k.label}
            </button>
          ))}
        </div>
        <label className="text-sm">
          From <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={inputClass} />
        </label>
        <label className="text-sm">
          To <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className={inputClass} />
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={onlyProblems} onChange={(e) => setOnlyProblems(e.target.checked)} className="size-5 accent-brand" />
          Out of limit only
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={showVoided} onChange={(e) => setShowVoided(e.target.checked)} className="size-5 accent-brand" />
          Show voided
        </label>
      </div>

      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[800px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">What</th>
              <th className="px-4 py-3 font-medium">Temperature</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Taken by</th>
              <th className="px-4 py-3 font-medium">Saved</th>
              <th className="px-4 py-3 font-medium">Corrective action</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={7} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && records.length === 0 && <tr><td colSpan={7} className="px-4 py-3 text-muted">No records in this period.</td></tr>}
            {records.map((r) => (
              <tr key={r.id} className={r.voided ? 'text-muted line-through' : ''}>
                <td className="px-4 py-3">{config.what(r)}</td>
                <td className="px-4 py-3 font-semibold tabular-nums">{config.temp(r)}</td>
                <td className="px-4 py-3">{r.voided ? <span className="font-medium no-underline">Voided</span> : <StatusBadge status={r.status} />}</td>
                <td className="px-4 py-3">{r.recorded_by_name}</td>
                <td className="px-4 py-3 text-sm">{formatDateTime(r.recorded_at)}<br /><span className="text-muted">{r.entered_by_name}</span></td>
                <td className="px-4 py-3 text-sm">
                  {r.corrective_action ? `${r.corrective_action.action_label}${r.corrective_action.signed_off_at ? ' (signed off)' : ' (waiting)'}` : ''}
                </td>
                <td className="px-4 py-3 text-right">
                  {!r.voided && (
                    <button onClick={() => setVoiding(r)} className="h-9 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">
                      Void / correct
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data && data.count > records.length && (
        <p className="mt-2 text-sm text-muted">Showing the first {records.length} of {data.count}. Narrow the dates to see the rest.</p>
      )}

      {voiding && (
        <VoidDialog
          kind={kind}
          endpoint={config.endpoint}
          valueField={config.valueField}
          entry={voiding}
          title={`${config.what(voiding)} · ${config.temp(voiding)}`}
          onClose={() => setVoiding(null)}
        />
      )}
    </div>
  )
}
