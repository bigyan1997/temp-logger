import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CloudCheck, CloudUpload, FilePlus2, FileText, FileUp, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../../api/client.js'
import { useStaffChoice } from '../../components/StaffPicker.jsx'
import { formatDay } from '../../lib/format.js'
import { FILE_ACCEPT } from '../ncr/Attachment.jsx'
import DriveLink from '../ncr/DriveLink.jsx'
import { uploadServiceFiles } from './NewService.jsx'
import ServiceDue from './ServiceDue.jsx'

const PAGE_SIZE = 50 // matches the server
const inputClass = 'h-10 rounded-lg border border-line bg-surface px-3 focus:border-brand focus:outline-2 focus:outline-brand'
const heading = 'px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted'

// A file as a small chip: opens the file, says whether the Google Drive copy is done, and has an X to delete it.
function FileChip({ file, onDelete }) {
  return (
    <li className={`inline-flex max-w-full items-center gap-2 rounded-lg border px-3 py-1.5 text-sm border-brand/40 bg-brand-soft`}>
      <FileText size={14} className="shrink-0 text-brand-dark" aria-hidden="true" />
      <a href={file.url} target="_blank" rel="noreferrer" title={file.original_name} className={`max-w-44 truncate hover:underline`}>
        {file.original_name}
      </a>
      {file.copy_status === 'waiting' && (
        <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-near">
          <CloudUpload size={12} aria-hidden="true" /> Syncing
        </span>
      )}
      {file.copy_status === 'saved' && <CloudCheck size={14} className="shrink-0 text-ok" aria-label="In Google Drive" />}
      <button type="button" onClick={onDelete} aria-label={`Delete ${file.original_name}`} className="grid size-5 shrink-0 place-items-center rounded text-muted hover:bg-white hover:text-bad">
        <X size={14} aria-hidden="true" />
      </button>
    </li>
  )
}

// Day staff: every service record, with its invoices. `embedded`: shown as a tab on the all-records page.
export default function ServiceRecords({ embedded = false }) {
  const notice = useLocation().state?.notice
  const queryClient = useQueryClient()
  const { staff, staffId, setStaffId } = useStaffChoice()
  const [search, setSearch] = useState('')
  const [kind, setKind] = useState('') // '', 'service' or 'repair'
  const [page, setPage] = useState(1)
  const [deleting, setDeleting] = useState(null) // { kind: 'record' | 'file', item }
  const [leftOver, setLeftOver] = useState([]) // problems cleaning up after a delete
  const [reason, setReason] = useState('')

  const query = `?page=${page}${search.trim() ? `&q=${encodeURIComponent(search.trim())}` : ''}${kind ? `&kind=${kind}` : ''}`
  const { data, isLoading } = useQuery({ queryKey: ['service-list', search, kind, page], queryFn: () => api(`/service-records/${query}`) })
  const services = data?.results ?? []

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['service-list'] })
    queryClient.invalidateQueries({ queryKey: ['service-due'] })
  }
  const addFiles = useMutation({
    mutationFn: ({ id, files }) => uploadServiceFiles(id, files, staffId),
    onSuccess: refresh,
  })
  const doDelete = useMutation({
    mutationFn: () => api(`/service-records/${deleting.kind === 'file' ? 'files/' : ''}${deleting.item.id}/delete/`, { method: 'POST', body: { reason, recorded_by: staffId } }),
    onSuccess: (result) => {
      setLeftOver(result.problems)
      setDeleting(null)
      setReason('')
      refresh()
    },
  })

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">Equipment Service Logs</h1>
          {data && <span className="rounded-full bg-brand-soft px-3 py-1 text-sm text-brand-dark">{data.count} record{data.count === 1 ? '' : 's'}</span>}
        </div>
        <div className="inline-flex flex-wrap items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-sm">
          <span className="size-2 rounded-full bg-ok" aria-hidden="true" />
          <label htmlFor="staff-name">Logged in as</label>
          <select id="staff-name" value={staffId} onChange={(e) => setStaffId(e.target.value)} className="rounded bg-transparent font-semibold focus:outline-2 focus:outline-brand">
            <option value="" disabled>Choose your name…</option>
            {staff.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <span className="text-muted">• Actions are recorded under your name</span>
        </div>
      </div>
      {!embedded && (
        <p className="mt-1 max-w-prose text-muted">
          Services and repairs of the coolrooms, freezers and other equipment: who did the work, when, and the invoice. Deleting asks for a reason and is kept in the audit log.
        </p>
      )}
      {notice && <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm">{notice}</p>}
      <ServiceDue />

      <div className="mt-4 flex flex-wrap items-end gap-4">
        {!embedded && (
          <Link to="/service/new" className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-dark">
            <FilePlus2 size={16} aria-hidden="true" /> New service record
          </Link>
        )}
        <DriveLink />
        <label className="text-sm">
          Type
          <select value={kind} onChange={(e) => { setKind(e.target.value); setPage(1) }} className={`${inputClass} ml-1`}>
            <option value="">All</option>
            <option value="service">Routine service</option>
            <option value="repair">Repair</option>
          </select>
        </label>
        <label className="text-sm">
          Search
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} placeholder="Equipment, who, invoice…" className={`${inputClass} ml-1 w-64`} />
        </label>
      </div>

      {leftOver.length > 0 && (
        <div role="alert" className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm">
          <p>It was deleted, but:</p>
          <ul className="list-disc pl-5">{leftOver.map((p) => <li key={p}>{p}</li>)}</ul>
        </div>
      )}
      {addFiles.error && <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{addFiles.error.message}</p>}

      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[1040px] text-left">
          <thead className="border-b border-line">
            <tr>
              <th className={heading}>No.</th>
              <th className={`${heading} whitespace-nowrap`}>Date</th>
              <th className={heading}>Equipment</th>
              <th className={heading}>Done by</th>
              <th className={heading}>Work done</th>
              <th className={heading}>Invoice &amp; attachments</th>
              <th className={heading}>Entered by</th>
              <th className={`${heading} text-right`}>Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={8} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && services.length === 0 && <tr><td colSpan={8} className="px-4 py-3 text-muted">No service records yet.</td></tr>}
            {services.map((s) => (
              <tr key={s.id} className="align-top hover:bg-brand-soft/50">
                <td className="whitespace-nowrap px-4 py-4 font-semibold">
                  <Link to={`/service/${s.id}`} className="text-brand-dark hover:underline">{s.number}</Link>
                </td>
                <td className="whitespace-nowrap px-4 py-4">{formatDay(s.service_date)}</td>
                <td className="px-4 py-4">
                  <span className="font-semibold">{s.equipment}</span>
                  <br />
                  <span className="text-xs text-muted">{s.kind_label}</span>
                </td>
                <td className="px-4 py-4">{s.serviced_by}</td>
                <td className="whitespace-pre-line px-4 py-4">
                  {s.work_done}
                </td>
                <td className="px-4 py-4">
                  {s.invoice_number && <p className="mb-2 font-semibold">{s.invoice_number}</p>}
                  <ul className="flex flex-col items-start gap-2">
                    {s.files.map((f) => (
                      <FileChip key={f.id} file={f} onDelete={() => setDeleting({ kind: 'file', item: f })} />
                    ))}
                  </ul>
                  {s.files.length === 0 && <p className="text-sm text-muted">No invoice attached.</p>}
                </td>
                <td className="px-4 py-4">{s.recorded_by_name}</td>
                <td className="whitespace-nowrap px-4 py-4 text-right">
                  <div className="flex justify-end gap-2">
                    <label
                      title="Add file"
                      className={`grid size-9 place-items-center rounded-lg border border-brand/40 bg-brand-soft text-brand-dark ${staffId ? 'cursor-pointer hover:bg-white' : 'pointer-events-none opacity-50'}`}
                    >
                      <FileUp size={16} aria-hidden="true" />
                      <span className="sr-only">Add file to {s.number}</span>
                      <input
                        type="file"
                        accept={FILE_ACCEPT}
                        multiple
                        disabled={!staffId}
                        className="sr-only"
                        onChange={(e) => {
                          addFiles.mutate({ id: s.id, files: [...e.target.files] })
                          e.target.value = ''
                        }}
                      />
                    </label>
                    <button
                      type="button"
                      title="Delete"
                      aria-label={`Delete ${s.number}`}
                      onClick={() => setDeleting({ kind: 'record', item: s })}
                      className="grid size-9 place-items-center rounded-lg border border-bad/40 text-bad hover:bg-red-50"
                    >
                      <Trash2 size={16} aria-hidden="true" />
                    </button>
                  </div>
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

      {deleting && (
        <form
          onSubmit={(e) => { e.preventDefault(); doDelete.mutate() }}
          className="mt-4 max-w-xl space-y-3 rounded-xl border border-line bg-surface p-4"
        >
          <p className="font-semibold">Delete {deleting.kind === 'file' ? deleting.item.original_name : `${deleting.item.number} and its files`} for good?</p>
          <p className="text-sm text-muted">{deleting.kind === 'file' ? 'The file is removed from this computer. ' : 'The record and its files are removed from this computer and the Google Drive folder goes to the Bin. '}The audit log keeps what was deleted and why. Say why.</p>
          <input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} autoFocus aria-label="Reason" className={`${inputClass} w-full`} />
          {!staffId && <p className="text-sm text-bad">Choose your name at the top first.</p>}
          {doDelete.error && <p role="alert" className="text-sm text-bad">{doDelete.error.message}</p>}
          <div className="flex gap-3">
            <button type="submit" disabled={reason.trim().length < 3 || !staffId || doDelete.isPending} className="h-10 rounded-lg bg-bad px-4 font-semibold text-white disabled:opacity-50">Delete for good</button>
            <button type="button" onClick={() => { setDeleting(null); setReason('') }} className="h-10 rounded-lg border border-line px-4 font-medium hover:bg-brand-soft">Cancel</button>
          </div>
        </form>
      )}
    </div>
  )
}
