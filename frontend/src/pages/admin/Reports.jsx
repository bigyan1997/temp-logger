import { FileText } from 'lucide-react'
import { useState } from 'react'
import { todayInSydney } from '../../lib/format.js'

const reports = [
  { kind: 'storage', title: 'Cold and frozen storage', table: 'Table 9', text: 'Four weeks per page, a column for each unit, like the paper sheet.' },
  { kind: 'receiving', title: 'Receiving stock', table: 'Table 10', text: 'A row for each day, starting with Sunday night, and a column for each supplier.' },
  { kind: 'dispatch', title: 'Dispatch', table: 'Table 11', text: 'A row for each day, starting with Sunday, and a column for each run.' },
]

const MAX_DAYS = 186 // keep in step with backend reports/grids.py

const daysAgo = (n) => {
  const d = new Date(todayInSydney())
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const inputClass = 'h-11 rounded-lg border border-line bg-surface px-3 focus:border-brand focus:outline-2 focus:outline-brand'

// PDF reports laid out like the paper tables, for auditors.
export default function Reports() {
  const [from, setFrom] = useState(daysAgo(27))
  const [to, setTo] = useState(todayInSydney())

  const days = (new Date(to) - new Date(from)) / 86_400_000
  const problem = days < 0 ? 'The start date is after the end date.' : days >= MAX_DAYS ? `Choose up to ${MAX_DAYS} days.` : ''

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold">Reports</h1>
      <p className="mt-1 text-muted">
        PDFs that look like the paper HACCP tables. They cover whole Sunday-to-Friday weeks, so the dates are rounded out to full weeks. Out-of-limit readings are starred in red, and the corrective actions are listed underneath.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-4">
        <label className="text-sm">
          From <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={inputClass} />
        </label>
        <label className="text-sm">
          To <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className={inputClass} />
        </label>
      </div>
      {problem && <p role="alert" className="mt-2 text-sm text-bad">{problem}</p>}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {reports.map((r) => (
          <section key={r.kind} className="flex flex-col rounded-xl border border-line bg-surface p-4">
            <p className="text-sm font-medium text-brand">{r.table}</p>
            <h2 className="font-semibold">{r.title}</h2>
            <p className="mt-1 flex-1 text-sm text-muted">{r.text}</p>
            <a
              href={problem ? undefined : `/api/reports/${r.kind}.pdf?from=${from}&to=${to}`}
              target="_blank"
              rel="noreferrer"
              aria-disabled={Boolean(problem)}
              className={`mt-4 inline-flex h-11 items-center justify-center gap-2 rounded-lg font-semibold text-white ${problem ? 'bg-muted' : 'bg-brand hover:bg-brand-dark'}`}
            >
              <FileText size={16} aria-hidden="true" /> Open PDF
            </a>
          </section>
        ))}
      </div>
    </div>
  )
}
