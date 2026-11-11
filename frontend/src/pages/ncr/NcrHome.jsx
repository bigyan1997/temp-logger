import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Download, Eye, FileDown, FilePlus2, Paperclip, TriangleAlert, XOctagon } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.js'
import { formatDay, todayInSydney } from '../../lib/format.js'
import DriveLink from './DriveLink.jsx'

const PAGE_SIZE = 50 // matches the server
const inputClass = 'h-10 rounded-lg border border-line bg-surface px-3 focus:border-brand focus:outline-2 focus:outline-brand'

// Every state has a shape and words as well as a colour.
export function StatusLabel({ status }) {
  if (status === 'closed') return <span className="inline-flex items-center gap-1 whitespace-nowrap font-medium text-ok"><CheckCircle2 size={14} aria-hidden="true" /> Closed</span>
  if (status === 'voided') return <span className="inline-flex items-center gap-1 whitespace-nowrap font-medium text-muted"><XOctagon size={14} aria-hidden="true" /> Voided</span>
  return <span className="inline-flex items-center gap-1 whitespace-nowrap font-medium text-near"><TriangleAlert size={14} aria-hidden="true" /> Open</span>
}

const daysAgo = (n) => {
  const d = new Date(todayInSydney())
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

// Day staff: the non-conformance reports. Open ones first by default. `embedded`: shown as a tab on the all-records page.
export default function NcrHome({ embedded = false }) {
  const [status, setStatus] = useState('open')
  const [search, setSearch] = useState('')
  const [showVoided, setShowVoided] = useState(false)
  const [page, setPage] = useState(1)
  const [from, setFrom] = useState(daysAgo(364))
  const [to, setTo] = useState(todayInSydney())

  const query = `?page=${page}${status === 'all' ? '' : `&status=${status}`}${search.trim() ? `&q=${encodeURIComponent(search.trim())}` : ''}${showVoided ? '&include_voided=1' : ''}`
  const { data, isLoading } = useQuery({ queryKey: ['ncr-list', status, search, showVoided, page], queryFn: () => api(`/non-conformances/${query}`) })
  const reports = data?.results ?? []
  const reset = (set) => (e) => {
    set(e.target.value)
    setPage(1)
  }
  const days = (new Date(to) - new Date(from)) / 86_400_000
  const pdfProblem = days < 0 ? 'The start date is after the end date.' : days > 365 ? 'The register covers up to a year.' : ''

  return (
    <div className="max-w-6xl">
      {!embedded && (
        <>
          <h1 className="text-2xl font-semibold">Non-conformance reports</h1>
          <p className="mt-1 max-w-prose text-muted">
            HACCP Table 5. A report is saved once and never changed. What happens next (manufacturer told, their answer, the corrective action, closing it) is added to it as dated follow-ups.
          </p>
        </>
      )}

      <div className="mt-4 flex flex-wrap items-end gap-4">
        {!embedded && (
          <Link to="/ncr/new" className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-dark">
            <FilePlus2 size={16} aria-hidden="true" /> New report
          </Link>
        )}
        <DriveLink />
        <label className="text-sm">
          Show
          <select value={status} onChange={reset(setStatus)} className={`${inputClass} ml-1`}>
            <option value="open">Open reports</option>
            <option value="closed">Closed reports</option>
            <option value="all">All reports</option>
          </select>
        </label>
        <label className="text-sm">
          Search
          <input value={search} onChange={reset(setSearch)} placeholder="Product, customer, manufacturer…" className={`${inputClass} ml-1 w-64`} />
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={showVoided} onChange={(e) => { setShowVoided(e.target.checked); setPage(1) }} className="size-5 accent-brand" />
          Show voided
        </label>
      </div>

      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[960px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">No.</th>
              <th className="whitespace-nowrap px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Product</th>
              <th className="px-4 py-3 font-medium">Customer</th>
              <th className="px-4 py-3 font-medium">Manufacturer</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">PDF</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={7} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && reports.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-3 text-muted">{status === 'open' ? 'No open reports.' : 'No reports found.'}</td></tr>
            )}
            {reports.map((r) => (
              <tr key={r.id} className={`hover:bg-brand-soft ${r.voided ? 'text-muted line-through' : ''}`}>
                <td className="whitespace-nowrap px-4 py-3 font-semibold no-underline">
                  <Link to={`/ncr/${r.id}`} className="text-brand-dark hover:underline">{r.number}</Link>
                </td>
                <td className="whitespace-nowrap px-4 py-3">{formatDay(r.date)}</td>
                <td className="px-4 py-3">
                  {r.product}
                  {r.photos.some((p) => !p.voided) && <Paperclip size={14} className="ml-2 inline text-muted" aria-label="Has photos" />}
                </td>
                <td className="px-4 py-3">{r.customer}</td>
                <td className="px-4 py-3">{r.manufacturer}</td>
                <td className="px-4 py-3 no-underline"><StatusLabel status={r.status} /></td>
                <td className="whitespace-nowrap px-4 py-3 no-underline">
                  <a href={`/api/non-conformances/${r.id}/pdf/`} target="_blank" rel="noreferrer" aria-label={`View ${r.number} PDF`} className="mr-3 inline-flex items-center gap-1 text-brand-dark hover:underline">
                    <Eye size={15} aria-hidden="true" /> View
                  </a>
                  <a href={`/api/non-conformances/${r.id}/pdf/`} download={`${r.number}.pdf`} aria-label={`Download ${r.number} PDF`} className="inline-flex items-center gap-1 text-brand-dark hover:underline">
                    <Download size={15} aria-hidden="true" /> Download
                  </a>
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

      <div className="mt-8 flex flex-wrap items-end gap-4 rounded-xl border border-line bg-surface p-4">
        <div>
          <p className="font-semibold">Table 5 register (PDF)</p>
          <p className="text-sm text-muted">Every report in the dates chosen, laid out like the paper table.</p>
        </div>
        <label className="text-sm">From <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={inputClass} /></label>
        <label className="text-sm">To <input type="date" value={to} max={todayInSydney()} onChange={(e) => setTo(e.target.value)} className={inputClass} /></label>
        <a
          href={pdfProblem ? undefined : `/api/non-conformances/register/?from=${from}&to=${to}`}
          target="_blank"
          rel="noreferrer"
          aria-disabled={Boolean(pdfProblem)}
          className={`inline-flex h-10 items-center gap-2 rounded-lg px-4 font-semibold text-white ${pdfProblem ? 'bg-muted' : 'bg-brand hover:bg-brand-dark'}`}
        >
          <FileDown size={16} aria-hidden="true" /> Open PDF
        </a>
        {pdfProblem && <p role="alert" className="w-full text-sm text-bad">{pdfProblem}</p>}
      </div>
    </div>
  )
}
