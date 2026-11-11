import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, CloudCheck, CloudUpload, FileDown, ImagePlus } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../../api/client.js'
import StaffPicker, { useStaffChoice } from '../../components/StaffPicker.jsx'
import VoidReasonDialog from '../../components/VoidReasonDialog.jsx'
import { formatDateTime, formatDay } from '../../lib/format.js'
import DriveLink from './DriveLink.jsx'
import { StatusLabel } from './NcrHome.jsx'
import { nowForInput, uploadPhotos } from './NewNcr.jsx'

const inputClass =
  'h-11 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'
const textClass =
  'w-full rounded-lg border border-line bg-surface px-3 py-2 text-base focus:border-brand focus:outline-2 focus:outline-brand'

const kinds = [
  { value: 'response', short: 'Response', label: 'Manufacturer response', timeLabel: 'When they replied', needsText: true },
  { value: 'action', short: 'Corrective action', label: 'Further corrective action', timeLabel: 'When', needsText: true },
  { value: 'notified', short: 'Notified', label: 'Manufacturer notified', timeLabel: 'Date and time the manufacturer was told', needsText: false },
  { value: 'note', label: 'Note', timeLabel: 'When', needsText: true },
  { value: 'closed', short: 'Sign off', label: 'Sign off and close the report', timeLabel: 'Date and time', needsText: false },
]

// A short label saying whether the second copy of a photo has reached Google Drive.
function CopyLabel({ photo }) {
  if (photo.copy_status === 'saved') {
    return <span className="inline-flex items-center gap-1 text-xs text-ok"><CloudCheck size={13} aria-hidden="true" /> In Google Drive</span>
  }
  if (photo.copy_status === 'waiting') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-near" title={photo.copy_error}>
        <CloudUpload size={13} aria-hidden="true" /> Waiting to copy to Google Drive
      </span>
    )
  }
  return null
}

export default function NcrDetail() {
  const { id } = useParams()
  const { state } = useLocation()
  const queryClient = useQueryClient()
  const { staff, staffId, setStaffId } = useStaffChoice()
  const [voiding, setVoiding] = useState(null) // { heading, title, endpoint }
  const { data: report, isLoading, error } = useQuery({ queryKey: ['ncr', id], queryFn: () => api(`/non-conformances/${id}/`) })

  // Saves a PDF of the report, as it is now, on this PC and in Google Drive.
  const saveToDrive = useMutation({ mutationFn: () => api(`/non-conformances/${id}/save_to_drive/`, { method: 'POST' }) })

  const addPhotos = useMutation({
    mutationFn: (files) => uploadPhotos(id, files, staffId),
    onSuccess: () => queryClient.invalidateQueries(),
  })

  if (isLoading) return <p className="text-muted">Loading…</p>
  if (error) return <p role="alert" className="text-bad">{error.message}</p>

  const closed = report.status === 'closed'
  const voided = report.voided
  const photos = report.photos.filter((p) => !p.voided && !p.update)
  const voidedPhotos = report.photos.filter((p) => p.voided)
  const updatePhotos = (update) => report.photos.filter((p) => !p.voided && p.update === update.id)
  const problem = !staffId ? 'Pick your name first.' : null

  return (
    <div className="max-w-4xl">
      <Link to="/ncr" className="text-sm text-brand-dark hover:underline">← All reports</Link>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{report.number} <span className="ml-2 text-base"><StatusLabel status={report.status} /></span></h1>
        <div className="flex gap-2">
          <a href={`/api/non-conformances/${report.id}/pdf/`} download={`${report.number}.pdf`} className="inline-flex h-10 items-center gap-2 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">
            <FileDown size={16} aria-hidden="true" /> Download PDF
          </a>
          <button
            onClick={() => saveToDrive.mutate()}
            disabled={saveToDrive.isPending}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft disabled:opacity-50"
          >
            <CloudUpload size={16} aria-hidden="true" /> {saveToDrive.isPending ? 'Saving…' : 'Upload to Drive'}
          </button>
          <DriveLink />
          {!voided && (
            <button
              onClick={() => setVoiding({ heading: 'Void this report', title: `${report.number} · ${report.product}`, endpoint: `/non-conformances/${report.id}/void/` })}
              className="h-10 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft"
            >
              Void
            </button>
          )}
        </div>
      </div>

      {saveToDrive.error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{saveToDrive.error.message}</p>}
      {saveToDrive.data && (
        <p role="status" className={`mt-3 rounded-lg px-3 py-2 text-sm ${saveToDrive.data.problems.length ? 'bg-amber-50 text-near' : 'bg-green-50 text-ok'}`}>
          {saveToDrive.data.saved.length > 0 && `Saved ${saveToDrive.data.name} to: ${saveToDrive.data.saved.join(', ')}. `}
          {saveToDrive.data.problems.join(' ')}
        </p>
      )}
      {state?.notice && <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-near">{state.notice}</p>}
      {voided && <p className="mt-3 whitespace-pre-line rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-bad">Voided: {report.void_reason}</p>}

      <dl className="mt-4 grid gap-x-6 gap-y-3 rounded-xl border border-line bg-surface p-5 sm:grid-cols-2">
        <Field label="Date" value={formatDay(report.date)} />
        <Field label="Product name / code" value={report.product} />
        <Field label="Customer" value={report.customer} />
        <Field label="Manufacturer" value={report.manufacturer} />
        <div className="sm:col-span-2"><Field label="Description of the problem" value={report.description} /></div>
        <Field label="Reported by" value={`${report.recorded_by_name}, ${formatDateTime(report.recorded_at)}`} />
      </dl>

      <h2 className="mb-2 mt-8 text-lg font-semibold">Photos</h2>
      {photos.length === 0 && <p className="text-muted">No photos.</p>}
      <ul className="flex flex-wrap gap-4">
        {photos.map((photo) => (
          <li key={photo.id} className="w-44">
            <a href={photo.url} target="_blank" rel="noreferrer">
              <img src={photo.url} alt={photo.original_name} loading="lazy" className="h-32 w-44 rounded-lg border border-line object-cover" />
            </a>
            <p className="mt-1 truncate text-sm" title={photo.original_name}>{photo.original_name}</p>
            <CopyLabel photo={photo} />
            {!voided && (
              <button
                onClick={() => setVoiding({ heading: 'Void this photo', title: photo.original_name, endpoint: `/non-conformances/photos/${photo.id}/void/` })}
                className="mt-1 block text-xs text-muted underline hover:text-ink"
              >
                Void
              </button>
            )}
          </li>
        ))}
      </ul>
      {voidedPhotos.length > 0 && (
        <p className="mt-2 text-sm text-muted">Voided photos (kept): {voidedPhotos.map((p) => `${p.original_name} (${p.void_reason})`).join(', ')}</p>
      )}
      {!voided && (
        <div className="mt-3">
          <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">
            <ImagePlus size={16} aria-hidden="true" /> {addPhotos.isPending ? 'Adding…' : 'Add photos'}
            <input
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              multiple
              disabled={!staffId || addPhotos.isPending}
              className="sr-only"
              onChange={(e) => {
                if (e.target.files.length) addPhotos.mutate([...e.target.files])
                e.target.value = ''
              }}
            />
          </label>
          {!staffId && <span className="ml-3 text-sm text-muted">Pick your name below first.</span>}
          {addPhotos.error && <p role="alert" className="mt-2 text-sm text-bad">{addPhotos.error.message}</p>}
        </div>
      )}

      <h2 className="mb-2 mt-8 text-lg font-semibold">What has happened since</h2>
      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
        {report.updates.length === 0 && <li className="px-4 py-3 text-muted">Nothing yet. Add the manufacturer being told, their response, or the corrective action below.</li>}
        {report.updates.map((update) => (
          <li key={update.id} className="px-4 py-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className={update.voided ? 'text-muted line-through' : ''}>
                <span className="font-semibold">{update.kind_label}</span>
                <span className="ml-2 text-sm text-muted">{formatDateTime(update.happened_at)} · {update.recorded_by_name}</span>
              </p>
              {!update.voided && !voided && (
                <button
                  onClick={() => setVoiding({ heading: 'Void this follow-up', title: `${update.kind_label} · ${formatDateTime(update.happened_at)}`, endpoint: `/non-conformances/updates/${update.id}/void/` })}
                  className="text-xs text-muted underline hover:text-ink"
                >
                  Void
                </button>
              )}
            </div>
            {update.text && <p className={`mt-1 whitespace-pre-line ${update.voided ? 'text-muted line-through' : ''}`}>{update.text}</p>}
            {updatePhotos(update).length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-3">
                {updatePhotos(update).map((photo) => (
                  <li key={photo.id} className="w-36">
                    <a href={photo.url} target="_blank" rel="noreferrer">
                      <img src={photo.url} alt={photo.original_name} loading="lazy" className="h-24 w-36 rounded-lg border border-line object-cover" />
                    </a>
                    <CopyLabel photo={photo} />
                  </li>
                ))}
              </ul>
            )}
            {update.voided && <p className="mt-1 whitespace-pre-line text-sm font-medium">Voided: {update.void_reason}</p>}
          </li>
        ))}
      </ul>

      {!voided && <FollowUpForm report={report} closed={closed} staff={staff} staffId={staffId} setStaffId={setStaffId} problem={problem} />}
      {voiding && <VoidReasonDialog {...voiding} onClose={() => setVoiding(null)} />}
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="whitespace-pre-line">{value || '-'}</dd>
    </div>
  )
}

// The steps run in the order of the paper form. The form always offers the next one that is missing, so most of the
// time nobody has to choose anything: write the response, then the corrective action, then sign off.
const STEPS = ['notified', 'response', 'action', 'closed']

function nextStep(report) {
  const done = (kind) => report.updates.some((u) => u.kind === kind && !u.voided)
  return STEPS.find((step) => !done(step)) ?? 'note'
}

// Add the next follow-up. Saving moves on to the next step by itself.
function FollowUpForm({ report, closed, staff, staffId, setStaffId, problem }) {
  const queryClient = useQueryClient()
  const next = closed ? 'note' : nextStep(report)
  const [picked, setPicked] = useState(null) // a step chosen by hand; null = just follow the order
  const kind = picked ?? next
  const [when, setWhen] = useState(nowForInput)
  const [text, setText] = useState('')
  const [files, setFiles] = useState([])
  const chosen = kinds.find((k) => k.value === kind)
  const steps = closed ? [] : STEPS.map((value) => kinds.find((k) => k.value === value))
  const isDone = (value) => report.updates.some((u) => u.kind === value && !u.voided)

  const save = useMutation({
    mutationFn: async (body) => {
      const update = await api(`/non-conformances/${report.id}/updates/`, { method: 'POST', body: { kind, text, recorded_by: staffId, happened_at: when, ...body } })
      // The follow-up is saved first, so a photo problem never loses what was typed.
      if (files.length) await uploadPhotos(report.id, files, staffId, update.id)
    },
    onSettled: () => queryClient.invalidateQueries(),
    onSuccess: () => {
      setText('')
      setFiles([])
      setWhen(nowForInput())
      setPicked(null)
    },
  })
  const missing = problem || (chosen.needsText && !text.trim() ? 'Write what happened.' : null)

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate({})
      }}
      className="mt-6 space-y-4 rounded-xl border border-line bg-surface p-5"
    >
      <h3 className="font-semibold">{closed ? 'This report is closed. You can still add a note.' : 'What happens next'}</h3>
      {!closed && (
        <ol className="flex flex-wrap gap-2" aria-label="Steps">
          {steps.map((step, index) => (
            <li key={step.value}>
              <button
                type="button"
                onClick={() => setPicked(step.value)}
                aria-current={kind === step.value ? 'step' : undefined}
                className={`inline-flex h-9 items-center gap-1 rounded-full border px-3 text-sm ${kind === step.value ? 'border-brand bg-brand-soft font-semibold' : 'border-line hover:bg-brand-soft'}`}
              >
                {isDone(step.value) ? <CheckCircle2 size={14} className="text-ok" aria-label="Done" /> : `${index + 1}.`} {step.short}
              </button>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() => setPicked('note')}
              aria-current={kind === 'note' ? 'step' : undefined}
              className={`inline-flex h-9 items-center rounded-full border px-3 text-sm ${kind === 'note' ? 'border-brand bg-brand-soft font-semibold' : 'border-line hover:bg-brand-soft'}`}
            >
              Just a note
            </button>
          </li>
        </ol>
      )}
      <p className="text-lg font-semibold">{chosen.label}</p>
      <div className="flex flex-wrap items-end gap-4">
        <div className="w-64">
          <StaffPicker staff={staff} staffId={staffId} setStaffId={setStaffId} />
        </div>
        <div className="mb-4">
          <label htmlFor="when" className="mb-1 block text-sm font-medium">{chosen.timeLabel}</label>
          <input id="when" type="datetime-local" value={when} max={nowForInput()} onChange={(e) => e.target.value && setWhen(e.target.value)} className={`${inputClass} w-64`} />
        </div>
      </div>
      {chosen.value !== 'notified' && (
        <div>
          <label htmlFor="text" className="mb-1 block text-sm font-medium">
            {chosen.value === 'closed' ? 'Closing note (optional)' : 'Details (required)'}
          </label>
          <textarea id="text" value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={4000} autoFocus className={textClass} />
          <p className="mt-1 text-xs text-muted">Enter starts a new line.</p>
        </div>
      )}
      {chosen.value !== 'closed' && (
        <div>
          <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">
            <ImagePlus size={16} aria-hidden="true" /> {chosen.value === 'response' ? 'Add the manufacturer’s photo' : 'Add a photo'} (optional)
            <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" multiple className="sr-only"
              onChange={(e) => { setFiles([...files, ...e.target.files]); e.target.value = '' }} />
          </label>
          {files.length > 0 && <span className="ml-3 text-sm">{files.map((f) => f.name).join(', ')} <button type="button" onClick={() => setFiles([])} className="ml-1 text-muted underline">remove</button></span>}
        </div>
      )}
      {save.error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{save.error.message}</p>}
      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" disabled={Boolean(missing) || save.isPending} className="h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark disabled:opacity-50">
          {save.isPending ? 'Saving…' : chosen.value === 'closed' ? 'Sign off and close' : chosen.value === 'note' ? 'Add note' : 'Save and go to next step'}
        </button>
        {chosen.value === 'action' && (
          <button
            type="button"
            disabled={Boolean(problem) || save.isPending}
            onClick={() => save.mutate({ text: 'None' })}
            className="h-11 rounded-lg border border-line px-5 font-medium hover:bg-brand-soft disabled:opacity-50"
          >
            No further action needed
          </button>
        )}
        {missing && <span className="text-sm text-muted">{missing}</span>}
      </div>
    </form>
  )
}
