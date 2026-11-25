import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImagePlus, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'
import EntryShell from '../../components/EntryShell.jsx'
import { enterMovesOn } from '../../lib/focusNext.js'
import { useActiveList } from '../../lib/useActiveList.js'
import { FILE_ACCEPT, FILE_HELP } from '../ncr/Attachment.jsx'
import DropZone from '../ncr/DropZone.jsx'

const inputClass =
  'h-12 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// The files, sent with the name of whoever is adding them.
export function uploadServiceFiles(serviceId, files, staffId) {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  form.append('recorded_by', staffId)
  return api(`/service-records/${serviceId}/add_files/`, { method: 'POST', body: form })
}

const megabytes = (bytes) => `${(bytes / (1024 * 1024)).toFixed(1)} MB`

// A new service record: what was serviced, who did the work, when, and the invoice (a PDF, photo or any document).
export default function NewService() {
  return (
    <EntryShell title="New service record" intro="Record a service or repair of a coolroom, freezer or other equipment. The Day is the day the work was done.">
      {({ staffId, date }) => <ServiceForm staffId={staffId} date={date} />}
    </EntryShell>
  )
}

function ServiceForm({ staffId, date }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: units = [] } = useActiveList('/units/')
  const [equipment, setEquipment] = useState('')
  const [servicedBy, setServicedBy] = useState('')
  const [workDone, setWorkDone] = useState('')
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [files, setFiles] = useState([])

  const save = useMutation({
    mutationFn: async () => {
      const service = await api('/service-records/', {
        method: 'POST',
        body: {
          recorded_by: staffId, service_date: date, equipment, serviced_by: servicedBy, work_done: workDone,
          invoice_number: invoiceNumber,
        },
      })
      // The service is saved before the files go up, so a file problem never loses what was typed.
      let notice = ''
      if (files.length) {
        try {
          await uploadServiceFiles(service.id, files, staffId)
        } catch (problem) {
          notice = `The service was saved, but the files could not be added: ${problem.message} Add them again from Records.`
        }
      }
      return { notice }
    },
    onSuccess: ({ notice }) => {
      queryClient.invalidateQueries()
      navigate('/service/records', { state: { notice } })
    },
  })

  const problem = !staffId ? 'Pick your name first.'
    : !equipment.trim() ? 'Say what was serviced.'
    : !servicedBy.trim() ? 'Say who did the service.'
    : !workDone.trim() ? 'Say what was done.'
    : null

  return (
    <form
      onKeyDown={enterMovesOn}
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
      className="max-w-3xl space-y-5 rounded-xl border border-line bg-surface p-5"
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="equipment" className="mb-1 block text-sm font-medium">What was serviced (required)</label>
          <input id="equipment" value={equipment} onChange={(e) => setEquipment(e.target.value)} list="equipment-list" autoFocus maxLength={100} className={inputClass} />
          <datalist id="equipment-list">
            {units.map((u) => <option key={u.id} value={u.name} />)}
          </datalist>
          <p className="mt-1 text-xs text-muted">Pick a coolroom or freezer, or type anything else.</p>
        </div>
        <div>
          <label htmlFor="serviced-by" className="mb-1 block text-sm font-medium">Who did the service (required)</label>
          <input id="serviced-by" value={servicedBy} onChange={(e) => setServicedBy(e.target.value)} maxLength={150} placeholder="Company or technician" className={inputClass} />
        </div>
      </div>

      <div>
        <label htmlFor="work-done" className="mb-1 block text-sm font-medium">What was done (required)</label>
        <textarea
          id="work-done"
          value={workDone}
          onChange={(e) => setWorkDone(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-base focus:border-brand focus:outline-2 focus:outline-brand"
        />
        <p className="mt-1 text-xs text-muted">Enter starts a new line.</p>
      </div>

      <div className="sm:w-1/2">
        <label htmlFor="invoice-number" className="mb-1 block text-sm font-medium">Invoice number</label>
        <input id="invoice-number" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} maxLength={60} className={inputClass} />
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">Invoice and other files</p>
        <DropZone onFiles={(dropped) => setFiles([...files, ...dropped])}>
          <label className="inline-flex h-11 cursor-pointer items-center gap-2 rounded-lg border border-line px-4 font-medium hover:bg-brand-soft">
            <ImagePlus size={18} aria-hidden="true" /> Choose invoice or files
            <input
              type="file"
              accept={FILE_ACCEPT}
              multiple
              className="sr-only"
              onChange={(e) => {
                setFiles([...files, ...e.target.files])
                e.target.value = '' // so the same file can be chosen again after removing it
              }}
            />
          </label>
        </DropZone>
        <p className="mt-1 text-xs text-muted">{FILE_HELP} A copy is also saved to Google Drive.</p>
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
          {save.isPending ? 'Saving…' : 'Save service record'}
        </button>
        {problem && <span className="text-sm text-muted">{problem}</span>}
      </div>
    </form>
  )
}
