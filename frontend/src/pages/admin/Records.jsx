import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import VoidDialog from '../../components/VoidDialog.jsx'
import { formatDateTime, formatDay, todayInSydney } from '../../lib/format.js'
import { formatTemp } from '../../lib/status.js'

// What differs between the three kinds of record.
const kinds = {
  storage: {
    label: 'Storage',
    endpoint: '/storage-readings/',
    filter: { param: 'unit', list: '/units/', all: 'All units', name: (u) => u.name },
    valueField: 'value',
    what: (r) => r.unit_name,
    when: (r) => formatDateTime(r.slot), // the day and time the reading was for
    temp: (r) => (r.not_used ? 'Not used' : formatTemp(r.value)),
  },
  receiving: {
    label: 'Receiving',
    endpoint: '/receiving-checks/',
    filter: { param: 'supplier', list: '/suppliers/', all: 'All suppliers', name: (s) => s.name },
    valueField: 'temp',
    what: (r) => r.supplier_name,
    when: (r) => formatDay(r.date),
    temp: (r) => (r.no_delivery ? 'No delivery' : formatTemp(r.temp)),
  },
  dispatch: {
    label: 'Dispatch',
    endpoint: '/dispatch-readings/',
    filter: { param: 'run', list: '/runs/', all: 'All runs', name: (r) => `Run ${r.code}` },
    valueField: 'temp',
    what: (r) => `Run ${r.run_code}`,
    when: (r) => formatDay(r.date),
    temp: (r) => formatTemp(r.temp),
  },
}

const PAGE_SIZE = 100 // matches the server

// "2026-11" -> the first and last day of that month, as the API wants them.
function monthRange(month) {
  const [year, number] = month.split('-').map(Number)
  const lastDay = new Date(Date.UTC(year, number, 0)).getUTCDate()
  return { from: `${month}-01`, to: `${month}-${String(lastDay).padStart(2, '0')}` }
}

// Move a month like "2026-11" forward or back.
function shiftMonth(month, by) {
  const [year, number] = month.split('-').map(Number)
  const moved = new Date(Date.UTC(year, number - 1 + by, 1))
  return `${moved.getUTCFullYear()}-${String(moved.getUTCMonth() + 1).padStart(2, '0')}`
}

const monthName = new Intl.DateTimeFormat('en-AU', { month: 'long', year: 'numeric', timeZone: 'UTC' })

const inputClass = 'h-10 rounded-lg border border-line bg-surface px-3 focus:border-brand focus:outline-2 focus:outline-brand'

export default function Records() {
  const [kind, setKind] = useState('storage')
  const thisMonth = todayInSydney().slice(0, 7)
  const [month, setMonth] = useState(thisMonth) // records are shown a month at a time
  const [page, setPage] = useState(1)
  const [onlyProblems, setOnlyProblems] = useState(false)
  const [showVoided, setShowVoided] = useState(false)
  const [voiding, setVoiding] = useState(null)
  const [itemId, setItemId] = useState('') // the unit, supplier or run to show (empty: all)
  const config = kinds[kind]

  // Every item of this kind, including deactivated ones, since they may still have records.
  const { data: items = [] } = useQuery({
    queryKey: ['admin-list', config.filter.list],
    queryFn: () => api(`${config.filter.list}?all=1`),
  })

  const { from, to } = monthRange(month)
  const query =
    `?from=${from}&to=${to}&page=${page}${onlyProblems ? '&status=out_of_limit' : ''}${showVoided ? '&include_voided=1' : ''}` +
    (itemId ? `&${config.filter.param}=${itemId}` : '')
  const { data, isLoading } = useQuery({
    queryKey: ['records', kind, month, page, onlyProblems, showVoided, itemId],
    queryFn: () => api(`${config.endpoint}${query}`),
  })
  const records = data?.results ?? []

  return (
    <div>
      <h1 className="text-2xl font-semibold">Records</h1>

      <div className="mt-4 flex flex-wrap items-end gap-4">
        <div role="tablist" aria-label="Kind of record" className="flex gap-1">
          {Object.entries(kinds).map(([key, k]) => (
            <button
              key={key}
              role="tab"
              aria-selected={kind === key}
              onClick={() => {
                setKind(key)
                setItemId('')
                setPage(1)
              }}
              className={`h-10 rounded-lg px-4 font-medium ${kind === key ? 'bg-brand text-white' : 'border border-line bg-surface hover:bg-brand-soft'}`}
            >
              {k.label}
            </button>
          ))}
        </div>
        <label className="text-sm">
          Show
          <select
            value={itemId}
            onChange={(e) => {
              setItemId(e.target.value)
              setPage(1)
            }}
            className={`${inputClass} ml-1`}
          >
            <option value="">{config.filter.all}</option>
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {config.filter.name(item)}
                {item.active ? '' : ' (deactivated)'}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-1" role="group" aria-label="Month">
          <button
            onClick={() => {
              setMonth(shiftMonth(month, -1))
              setPage(1)
            }}
            aria-label="Previous month"
            className="grid size-10 place-items-center rounded-lg border border-line bg-surface hover:bg-brand-soft"
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </button>
          <input
            type="month"
            value={month}
            max={thisMonth}
            aria-label="Month"
            onChange={(e) => {
              if (e.target.value) {
                setMonth(e.target.value)
                setPage(1)
              }
            }}
            className={inputClass}
          />
          <button
            onClick={() => {
              setMonth(shiftMonth(month, 1))
              setPage(1)
            }}
            disabled={month >= thisMonth}
            aria-label="Next month"
            className="grid size-10 place-items-center rounded-lg border border-line bg-surface hover:bg-brand-soft disabled:opacity-40"
          >
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </div>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={onlyProblems} onChange={(e) => {
              setOnlyProblems(e.target.checked)
              setPage(1)
            }} className="size-5 accent-brand" />
          Out of limit only
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={showVoided} onChange={(e) => {
              setShowVoided(e.target.checked)
              setPage(1)
            }} className="size-5 accent-brand" />
          Show voided
        </label>
      </div>

      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[900px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">What</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Temperature</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Taken by</th>
              <th className="px-4 py-3 font-medium">Saved</th>
              <th className="px-4 py-3 font-medium">Corrective action / changes</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={8} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && records.length === 0 && <tr><td colSpan={8} className="px-4 py-3 text-muted">No records in this period.</td></tr>}
            {records.map((r) => (
              <tr key={r.id} className={r.voided ? 'text-muted line-through' : ''}>
                <td className="px-4 py-3">{config.what(r)}</td>
                <td className="whitespace-nowrap px-4 py-3">{config.when(r)}</td>
                <td className="px-4 py-3 font-semibold tabular-nums">{config.temp(r)}</td>
                <td className="px-4 py-3">{r.voided ? <span className="font-medium no-underline">Voided</span> : <StatusBadge status={r.status} />}</td>
                <td className="px-4 py-3">{r.recorded_by_name}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm">{formatDateTime(r.recorded_at)}<br /><span className="text-muted">{r.entered_by_name}</span></td>
                <td className="px-4 py-3 text-sm">
                  {r.corrective_action && (
                    <p>
                      {r.corrective_action.action_label}
                      {r.corrective_action.notes && <span className="text-muted">: {r.corrective_action.notes}</span>}
                    </p>
                  )}
                  {r.correction && (
                    <p className="no-underline">
                      <span className="font-medium">Corrected</span> from {r.correction.was}
                      {r.correction.reason && <span className="text-muted">: {r.correction.reason}</span>}
                    </p>
                  )}
                  {r.voided && r.void_reason && <p className="no-underline">Voided: {r.void_reason}</p>}
                </td>
                <td className="px-4 py-3 text-right">
                  {!r.voided && (
                    <button onClick={() => setVoiding(r)} className="h-9 whitespace-nowrap rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">
                      Void / correct
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
          <p>
            {data.count === 0 ? 'No records' : `${data.count} record${data.count === 1 ? '' : 's'}`} in {monthName.format(new Date(`${from}T00:00:00Z`))}
          </p>
          {data.count > PAGE_SIZE && (
            <div className="flex items-center gap-2">
              <button onClick={() => setPage(page - 1)} disabled={!data.previous} className="h-9 rounded-lg border border-line px-3 font-medium text-ink hover:bg-brand-soft disabled:opacity-40">
                Previous
              </button>
              <span>
                Page {page} of {Math.ceil(data.count / PAGE_SIZE)}
              </span>
              <button onClick={() => setPage(page + 1)} disabled={!data.next} className="h-9 rounded-lg border border-line px-3 font-medium text-ink hover:bg-brand-soft disabled:opacity-40">
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {voiding && (
        <VoidDialog
          kind={kind}
          endpoint={config.endpoint}
          valueField={config.valueField}
          entry={voiding}
          title={`${config.what(voiding)} · ${config.when(voiding)} · ${config.temp(voiding)}`}
          onClose={() => setVoiding(null)}
        />
      )}
    </div>
  )
}
