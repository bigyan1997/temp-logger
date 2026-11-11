import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImagePlus, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import EntryShell from '../../components/EntryShell.jsx'
import { enterMovesOn } from '../../lib/focusNext.js'
import { useActiveList } from '../../lib/useActiveList.js'

const inputClass =
  'h-12 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// The photos, sent with the name of whoever is adding them. Used here and on the report's own page.
export function uploadPhotos(reportId, files, staffId, updateId) {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  form.append('recorded_by', staffId)
  if (updateId) form.append('update', updateId) // the photo belongs to a follow-up, e.g. the manufacturer's response
  return api(`/non-conformances/${reportId}/add_photos/`, { method: 'POST', body: form })
}

// The date and time right now, for a "datetime-local" box (local to this computer).
export const nowForInput = () => {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}

const megabytes = (bytes) => `${(bytes / (1024 * 1024)).toFixed(1)} MB`

// A new report, like the paper Table 5: what the product is, who it was for, what went wrong, and photos.
export default function NewNcr() {
  return (
    <EntryShell title="New non-conformance report">
      {({ staffId, date }) => <ReportForm staffId={staffId} date={date} />}
    </EntryShell>
  )
}

function ReportForm({ staffId, date }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: suppliers = [] } = useActiveList('/suppliers/')
  const [product, setProduct] = useState('')
  const [customer, setCustomer] = useState('')
  const [manufacturer, setManufacturer] = useState('')
  const [description, setDescription] = useState('')
  const [files, setFiles] = useState([])
  const [notified, setNotified] = useState(false)
  const [notifiedAt, setNotifiedAt] = useState(nowForInput)

  const save = useMutation({
    mutationFn: async () => {
      const report = await api('/non-conformances/', {
        method: 'POST',
        body: { date, recorded_by: staffId, product, customer, manufacturer, description, ...(notified ? { notified_at: notifiedAt } : {}) },
      })
      // The report is saved before the photos go up, so a photo problem never loses what was typed.
      let notice = ''
      if (files.length) {
        try {
          await uploadPhotos(report.id, files, staffId)
        } catch (problem) {
          notice = `The report was saved, but the photos could not be added: ${problem.message} You can add them below.`
        }
      }
      return { report, notice }
    },
    onSuccess: ({ report, notice }) => {
      queryClient.invalidateQueries()
      navigate(`/ncr/${report.id}`, { state: { notice } })
    },
  })

  const problem = !staffId ? 'Pick your name first.' : !product.trim() ? 'Say which product it is.' : !description.trim() ? 'Describe the problem.' : null

  return (
    <form
      onKeyDown={enterMovesOn}
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
      className="max-w-3xl space-y-5 rounded-xl border border-line bg-surface p-5"
    >
      <div>
        <label htmlFor="product" className="mb-1 block text-sm font-medium">Product name / code (required)</label>
        <input id="product" value={product} onChange={(e) => setProduct(e.target.value)} autoFocus maxLength={200} className={inputClass} />
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="customer" className="mb-1 block text-sm font-medium">Customer</label>
          <input id="customer" value={customer} onChange={(e) => setCustomer(e.target.value)} maxLength={150} className={inputClass} />
        </div>
        <div>
          <label htmlFor="manufacturer" className="mb-1 block text-sm font-medium">Manufacturer</label>
          <input id="manufacturer" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} list="manufacturers" maxLength={150} className={inputClass} />
          <datalist id="manufacturers">
            {suppliers.map((s) => <option key={s.id} value={s.name} />)}
          </datalist>
        </div>
      </div>
      <div>
        <label htmlFor="description" className="mb-1 block text-sm font-medium">Description of the problem (required)</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={5}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-base focus:border-brand focus:outline-2 focus:outline-brand"
        />
        <p className="mt-1 text-xs text-muted">Enter starts a new line.</p>
      </div>

      <div>
        <fieldset>
          <legend className="mb-1 text-sm font-medium">Has the manufacturer been notified?</legend>
          <div className="flex gap-3">
            {[{ value: true, label: 'Yes' }, { value: false, label: 'No' }].map((choice) => (
              <label key={choice.label} className={`inline-flex h-11 min-w-20 cursor-pointer items-center justify-center gap-2 rounded-lg border px-4 font-medium ${notified === choice.value ? 'border-brand bg-brand-soft' : 'border-line hover:bg-brand-soft'}`}>
                <input type="radio" name="notified" checked={notified === choice.value} onChange={() => setNotified(choice.value)} className="size-4 accent-brand" />
                {choice.label}
              </label>
            ))}
          </div>
        </fieldset>
        {notified && (
          <div className="mt-2">
            <label htmlFor="notified-at" className="mb-1 block text-sm">Date and time they were told</label>
            <input id="notified-at" type="datetime-local" value={notifiedAt} max={nowForInput()} onChange={(e) => e.target.value && setNotifiedAt(e.target.value)} className={`${inputClass} w-64`} />
          </div>
        )}
        <p className="mt-1 text-xs text-muted">Not told yet? Leave it on No and add it later from the report.</p>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">Photos (if available)</p>
        <label className="inline-flex h-11 cursor-pointer items-center gap-2 rounded-lg border border-line px-4 font-medium hover:bg-brand-soft">
          <ImagePlus size={18} aria-hidden="true" /> Choose photos
          <input
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            multiple
            className="sr-only"
            onChange={(e) => {
              setFiles([...files, ...e.target.files])
              e.target.value = '' // so the same photo can be chosen again after removing it
            }}
          />
        </label>
        <p className="mt-1 text-xs text-muted">JPG, PNG, GIF or WEBP, up to 10 MB each. A copy is also saved to Google Drive.</p>
        {files.length > 0 && (
          <ul className="mt-2 space-y-1 text-sm">
            {files.map((file, index) => (
              <li key={`${file.name}-${index}`} className="flex items-center gap-2">
                <span>{file.name}</span>
                <span className="text-muted">{megabytes(file.size)}</span>
                <button type="button" onClick={() => setFiles(files.filter((_, i) => i !== index))} aria-label={`Remove ${file.name}`} className="grid size-6 place-items-center rounded hover:bg-brand-soft">
                  <X size={14} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {save.error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{save.error.message}</p>}
      <div className="flex items-center gap-4">
        <button type="submit" disabled={Boolean(problem) || save.isPending} className="h-12 rounded-lg bg-brand px-6 font-semibold text-white hover:bg-brand-dark disabled:opacity-50">
          {save.isPending ? 'Saving…' : 'Save report'}
        </button>
        {problem && <span className="text-sm text-muted">{problem}</span>}
      </div>
    </form>
  )
}
