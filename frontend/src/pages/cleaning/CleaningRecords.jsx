import { useQuery } from '@tanstack/react-query'
import { FileDown } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api/client.js'
import VoidReasonDialog from '../../components/VoidReasonDialog.jsx'
import { formatDateTime, formatDay, todayInSydney } from '../../lib/format.js'

const PAGE_SIZE = 100 // matches the server
const MAX_DAYS = 186 // keep in step with backend reports/grids.py
const inputClass = 'h-10 rounded-lg border border-line bg-surface px-3 focus:border-brand focus:outline-2 focus:outline-brand'

const daysAgo = (n) => {
  const d = new Date(todayInSydney())
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

// Day staff: every cleaning tick, with Void and the Table 8 PDF for the dates chosen.
// `embedded`: shown as a tab on the all-records page, which supplies the heading.
export default function CleaningRecords({ embedded = false }) {
  const [from, setFrom] = useState(daysAgo(34)) // five weeks, one sheet of the paper table
  const [to, setTo] = useState(todayInSydney())
  const [taskId, setTaskId] = useState('')
  const [showVoided, setShowVoided] = useState(false)
  const [page, setPage] = useState(1)
  const [voiding, setVoiding] = useState(null)

  const { data: tasks = [] } = useQuery({ queryKey: ['admin-list', '/cleaning-tasks/'], queryFn: () => api('/cleaning-tasks/?all=1') })
  const query = `?from=${from}&to=${to}&page=${page}${taskId ? `&task=${taskId}` : ''}${showVoided ? '&include_voided=1' : ''}`
  const { data, isLoading } = useQuery({ queryKey: ['cleaning-records', from, to, taskId, showVoided, page], queryFn: () => api(`/cleaning-checks/${query}`) })
  const records = data?.results ?? []

  const days = (new Date(to) - new Date(from)) / 86_400_000
  const pdfProblem = days < 0 ? 'The start date is after the end date.' : days >= MAX_DAYS ? `The PDF covers up to ${MAX_DAYS} days.` : ''
  const changed = (set) => (e) => {
    set(e.target.value)
    setPage(1)
  }

  return (
    <div className="max-w-6xl">
      {!embedded && (
        <>
          <h1 className="text-2xl font-semibold">Cleaning records</h1>
          <p className="mt-1 max-w-prose text-muted">HACCP Table 8. Each tick is kept here. The PDF looks like the paper table.</p>
        </>
      )}

      <div className="mt-4 flex flex-wrap items-end gap-4">
        <label className="text-sm">From <input type="date" value={from} onChange={changed(setFrom)} className={inputClass} /></label>
        <label className="text-sm">To <input type="date" value={to} max={todayInSydney()} onChange={changed(setTo)} className={inputClass} /></label>
        <label className="text-sm">
          Task
          <select value={taskId} onChange={changed(setTaskId)} className={`${inputClass} ml-1`}>
            <option value="">All tasks</option>
            {tasks.map((task) => (
              <option key={task.id} value={task.id}>{task.name}{task.active ? '' : ' (deactivated)'}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={showVoided} onChange={(e) => { setShowVoided(e.target.checked); setPage(1) }} className="size-5 accent-brand" />
          Show voided
        </label>
        <a
          href={pdfProblem ? undefined : `/api/cleaning-checks/pdf/?from=${from}&to=${to}`}
          target="_blank"
          rel="noreferrer"
          aria-disabled={Boolean(pdfProblem)}
          className={`inline-flex h-10 items-center gap-2 rounded-lg px-4 font-semibold text-white ${pdfProblem ? 'bg-muted' : 'bg-brand hover:bg-brand-dark'}`}
        >
          <FileDown size={16} aria-hidden="true" /> Table 8 PDF
        </a>
      </div>
      {pdfProblem && <p role="alert" className="mt-2 text-sm text-bad">{pdfProblem}</p>}

      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[760px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="whitespace-nowrap px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Done by</th>
              <th className="px-4 py-3 font-medium">Saved</th>
              <th className="px-4 py-3 font-medium">Note</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={6} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && records.length === 0 && <tr><td colSpan={6} className="px-4 py-3 text-muted">No records in this period.</td></tr>}
            {records.map((r) => (
              <tr key={r.id} className={r.voided ? 'text-muted line-through' : ''}>
                <td className="whitespace-nowrap px-4 py-3">{formatDay(r.date)}</td>
                <td className="px-4 py-3">{r.task_name}</td>
                <td className="px-4 py-3">{r.recorded_by_name}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm">{formatDateTime(r.recorded_at)}<br /><span className="text-muted">{r.entered_by_name}</span></td>
                <td className="px-4 py-3 text-sm">
                  <span className="whitespace-pre-line">{r.note}</span>
                  {r.voided && <p className="font-medium no-underline">Voided: {r.void_reason}</p>}
                </td>
                <td className="px-4 py-3 text-right no-underline">
                  {!r.voided && (
                    <button onClick={() => setVoiding(r)} className="h-9 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">Void</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.count > PAGE_SIZE && (
        <div className="mt-3 flex items-center gap-3 text-sm text-muted">
          <button onClick={() => setPage(page - 1)} disabled={!data.previous} className="h-9 rounded-lg border border-line px-3 font-medium text-ink hover:bg-brand-soft disabled:opacity-40">Previous</button>
          <span>Page {page} of {Math.ceil(data.count / PAGE_SIZE)}</span>
          <button onClick={() => setPage(page + 1)} disabled={!data.next} className="h-9 rounded-lg border border-line px-3 font-medium text-ink hover:bg-brand-soft disabled:opacity-40">Next</button>
        </div>
      )}

      {voiding && (
        <VoidReasonDialog
          heading="Void this entry"
          title={`${voiding.task_name} · ${formatDay(voiding.date)}. Voiding lets the task be ticked again for that day.`}
          endpoint={`/cleaning-checks/${voiding.id}/void/`}
          onClose={() => setVoiding(null)}
        />
      )}
    </div>
  )
}
