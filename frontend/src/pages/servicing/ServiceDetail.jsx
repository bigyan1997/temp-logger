import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CloudCheck, CloudUpload, ImagePlus, Pencil } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../api/client.js'
import StaffPicker, { useStaffChoice } from '../../components/StaffPicker.jsx'
import { formatDay, todayInSydney } from '../../lib/format.js'
import { FILE_ACCEPT, FILE_HELP } from '../ncr/Attachment.jsx'
import Attachment from '../ncr/Attachment.jsx'
import DropZone from '../ncr/DropZone.jsx'
import { uploadServiceFiles } from './NewService.jsx'

const inputClass =
  'h-12 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// One service record: its details (which can be corrected), and its invoices, which open in a new tab.
export default function ServiceDetail() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const { staff, staffId, setStaffId } = useStaffChoice()
  const [editing, setEditing] = useState(false)

  const { data: service, isLoading, error } = useQuery({ queryKey: ['service', id], queryFn: () => api(`/service-records/${id}/`) })
  const refresh = () => queryClient.invalidateQueries()

  const addFiles = useMutation({ mutationFn: (files) => uploadServiceFiles(id, files, staffId), onSuccess: refresh })

  if (isLoading) return <p className="text-muted">Loading…</p>
  if (error) return <p role="alert" className="text-bad">{error.message}</p>

  const files = service.files
  return (
    <div className="max-w-3xl">
      <Link to="/service/records" className="inline-flex items-center gap-1 text-sm text-brand-dark hover:underline">
        <ArrowLeft size={14} aria-hidden="true" /> All service records
      </Link>
      <h1 className="mt-2 text-2xl font-semibold">{service.number}: {service.equipment}</h1>

      <div className="mt-4 w-64"><StaffPicker staff={staff} staffId={staffId} setStaffId={setStaffId} /></div>
      <p className="-mt-2 mb-4 text-xs text-muted">Your name is kept in the audit log when you edit or add a file.</p>

      {editing ? (
        <EditForm service={service} staffId={staffId} onDone={() => { setEditing(false); refresh() }} />
      ) : (
        <div className="rounded-xl border border-line bg-surface p-5">
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <Item label="Date">{formatDay(service.service_date)}</Item>
            <Item label="Type">{service.kind_label}</Item>
            <Item label="Equipment">{service.equipment}</Item>
            <Item label="Done by">{service.serviced_by}</Item>
            <Item label="Invoice number">{service.invoice_number || '-'}</Item>
            <Item label="Entered by">{service.recorded_by_name}</Item>
            <div className="sm:col-span-2"><Item label="Work done"><span className="whitespace-pre-line">{service.work_done}</span></Item></div>
          </dl>
          <button type="button" onClick={() => setEditing(true)} className="mt-4 inline-flex h-10 items-center gap-2 rounded-lg border border-line px-4 font-medium hover:bg-brand-soft">
            <Pencil size={16} aria-hidden="true" /> Edit details
          </button>
        </div>
      )}

      <h2 className="mt-8 text-lg font-semibold">Invoice and files</h2>
      {files.length === 0 && <p className="mt-2 text-muted">No files attached.</p>}
      <ul className="mt-3 flex flex-wrap gap-4">
        {files.map((f) => (
          <li key={f.id} className="w-44">
            <Attachment photo={f} size="h-28 w-44" />
            <a href={f.url} target="_blank" rel="noreferrer" className="mt-1 block truncate text-sm text-brand-dark hover:underline" title={f.original_name}>{f.original_name}</a>
            <p className="inline-flex items-center gap-1 text-xs text-muted">
              {f.copy_status === 'saved' && <><CloudCheck size={12} aria-hidden="true" /> In Google Drive</>}
              {f.copy_status === 'waiting' && <><CloudUpload size={12} aria-hidden="true" /> Waiting for Google Drive</>}
            </p>
          </li>
        ))}
      </ul>

      <div className="mt-4">
        <DropZone disabled={!staffId} onFiles={(dropped) => addFiles.mutate(dropped)}>
          <label className={`inline-flex h-11 items-center gap-2 rounded-lg border border-line px-4 font-medium ${staffId ? 'cursor-pointer hover:bg-brand-soft' : 'opacity-50'}`}>
            <ImagePlus size={18} aria-hidden="true" /> Add invoice or files
            <input
              type="file"
              accept={FILE_ACCEPT}
              multiple
              disabled={!staffId}
              className="sr-only"
              onChange={(e) => {
                addFiles.mutate([...e.target.files])
                e.target.value = ''
              }}
            />
          </label>
        </DropZone>
        <p className="mt-1 text-xs text-muted">{FILE_HELP} To remove a file, use the X on its chip on the Service records page.</p>
        {!staffId && <p className="text-sm text-muted">Pick your name first.</p>}
        {addFiles.isPending && <p className="text-sm text-muted">Adding…</p>}
        {addFiles.error && <p role="alert" className="mt-1 text-sm text-bad">{addFiles.error.message}</p>}
      </div>
    </div>
  )
}

function Item({ label, children }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  )
}

function EditForm({ service, staffId, onDone }) {
  const [kind, setKind] = useState(service.kind)
  const [equipment, setEquipment] = useState(service.equipment)
  const [servicedBy, setServicedBy] = useState(service.serviced_by)
  const [date, setDate] = useState(service.service_date)
  const [workDone, setWorkDone] = useState(service.work_done)
  const [invoiceNumber, setInvoiceNumber] = useState(service.invoice_number)

  const save = useMutation({
    mutationFn: () => api(`/service-records/${service.id}/edit/`, {
      method: 'POST',
      body: { recorded_by: staffId, kind, equipment, serviced_by: servicedBy, service_date: date, work_done: workDone, invoice_number: invoiceNumber },
    }),
    onSuccess: onDone,
  })
  const problem = !staffId ? 'Pick your name first.' : !equipment.trim() || !servicedBy.trim() || !workDone.trim() ? 'Fill in what, who and the work done.' : null

  return (
    <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="space-y-4 rounded-xl border border-line bg-surface p-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium">Type of visit
          <select value={kind} onChange={(e) => setKind(e.target.value)} className={`${inputClass} mt-1 font-normal`}>
            <option value="service">Routine service</option>
            <option value="repair">Repair</option>
          </select>
        </label>
        <label className="text-sm font-medium">What was serviced
          <input value={equipment} onChange={(e) => setEquipment(e.target.value)} maxLength={100} autoFocus className={`${inputClass} mt-1 font-normal`} />
        </label>
        <label className="text-sm font-medium">Who did the service
          <input value={servicedBy} onChange={(e) => setServicedBy(e.target.value)} maxLength={150} className={`${inputClass} mt-1 font-normal`} />
        </label>
        <label className="text-sm font-medium">Date
          <input type="date" value={date} max={todayInSydney()} onChange={(e) => e.target.value && setDate(e.target.value)} className={`${inputClass} mt-1 font-normal`} />
        </label>
        <label className="text-sm font-medium">Invoice number
          <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} maxLength={60} className={`${inputClass} mt-1 font-normal`} />
        </label>
      </div>
      <label className="block text-sm font-medium">What was done
        <textarea value={workDone} onChange={(e) => setWorkDone(e.target.value)} rows={4} className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-base font-normal focus:border-brand focus:outline-2 focus:outline-brand" />
      </label>
      {save.error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{save.error.message}</p>}
      <div className="flex items-center gap-3">
        <button type="submit" disabled={Boolean(problem) || save.isPending} className="h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark disabled:opacity-50">
          {save.isPending ? 'Saving…' : 'Save changes'}
        </button>
        <button type="button" onClick={onDone} className="h-11 rounded-lg border border-line px-5 font-medium hover:bg-brand-soft">Cancel</button>
        {problem && <span className="text-sm text-muted">{problem}</span>}
      </div>
      <p className="text-xs text-muted">The old and new values are kept in the Servicing audit log.</p>
    </form>
  )
}
