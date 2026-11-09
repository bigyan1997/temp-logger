import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FileDown, XOctagon } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api/client.js'
import { formatDateTime, formatDay } from '../../lib/format.js'

// Day staff: every calibration done so far, with its PDF and Void. Kept apart from the Temperature Logger's records.
// `embedded`: shown as a tab on the all-records page, which supplies the heading.
export default function CalibrationRecords({ embedded = false }) {
  const [voiding, setVoiding] = useState(null)
  const { data, isLoading } = useQuery({
    queryKey: ['calibrations'],
    queryFn: () => api('/calibrations/?include_voided=1'),
  })
  const calibrations = data?.results ?? []

  return (
    <div className="max-w-6xl">
      {!embedded && (
        <>
          <h1 className="text-2xl font-semibold">Calibration records</h1>
          <p className="mt-1 max-w-prose text-muted">
            HACCP Table 14 forms. Each one is kept here, can be downloaded as a PDF, and a copy is saved to Drive.
          </p>
        </>
      )}

      <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[820px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="whitespace-nowrap px-4 py-3 font-medium">Date</th>
              <th className="whitespace-nowrap px-4 py-3 font-medium">Probe in ice water</th>
              <th className="whitespace-nowrap px-4 py-3 font-medium">Result</th>
              <th className="whitespace-nowrap px-4 py-3 font-medium">Gauges checked</th>
              <th className="whitespace-nowrap px-4 py-3 font-medium">Done by</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={6} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && calibrations.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-3 text-muted">No calibrations yet. Click New calibration to do the first one.</td></tr>
            )}
            {calibrations.map((c) => (
              <tr key={c.id} className={c.voided ? 'text-muted line-through' : ''}>
                <td className="whitespace-nowrap px-4 py-3">{formatDay(c.date)}</td>
                <td className="whitespace-nowrap px-4 py-3 tabular-nums">
                  {Number(c.probe_reading).toFixed(1)} °C
                  <span className="text-muted"> ({Number(c.probe_difference) > 0 ? '+' : ''}{Number(c.probe_difference).toFixed(1)})</span>
                </td>
                <td className="px-4 py-3 text-sm no-underline">
                  {c.voided ? (
                    <p className="font-medium">Voided: {c.void_reason}</p>
                  ) : c.passed ? (
                    <span className="inline-flex items-center gap-1 whitespace-nowrap font-medium text-ok"><CheckCircle2 size={14} aria-hidden="true" /> Passed</span>
                  ) : (
                    <>
                      <span className="inline-flex items-center gap-1 font-medium text-bad"><XOctagon size={14} aria-hidden="true" /> Outside the margin</span>
                      <p className="text-muted">{c.action_label}: {c.action_notes}</p>
                    </>
                  )}
                </td>
                <td className="px-4 py-3">{c.gauges.length ? c.gauges.map((g) => g.unit_name).join(', ') : 'None'}</td>
                <td className="px-4 py-3 text-sm">
                  {c.recorded_by_name}
                  <br />
                  <span className="whitespace-nowrap text-muted">{formatDateTime(c.recorded_at)}</span>
                </td>
                <td className="px-4 py-3 no-underline">
                  <div className="flex items-center justify-end gap-2">
                    <a
                      href={`/api/calibrations/${c.id}/pdf/`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex h-9 items-center gap-1 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft"
                    >
                      <FileDown size={16} aria-hidden="true" /> PDF
                    </a>
                    {!c.voided && (
                      <button onClick={() => setVoiding(c)} className="h-9 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">
                        Void
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {voiding && <VoidCalibration calibration={voiding} onClose={() => setVoiding(null)} />}
    </div>
  )
}

// Cancel a calibration done by mistake. It stays in the list, marked void, and is written to the audit log.
function VoidCalibration({ calibration, onClose }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const submit = useMutation({
    mutationFn: () => api(`/calibrations/${calibration.id}/void/`, { method: 'POST', body: { reason } }),
    onSuccess: () => {
      queryClient.invalidateQueries()
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-ink/40 p-4" role="dialog" aria-modal="true" aria-label="Void calibration">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit.mutate()
        }}
        className="w-full max-w-lg rounded-xl bg-surface p-5 shadow-lg"
      >
        <h2 className="text-lg font-semibold">Void this calibration</h2>
        <p className="mt-1 text-muted">{formatDay(calibration.date)} · {Number(calibration.probe_reading).toFixed(1)} °C</p>
        <p className="mt-1 text-sm text-muted">It stays in the list, marked void, and the change is written to the audit log. A voided calibration does not count towards the 6-monthly due date.</p>
        <label htmlFor="void-reason" className="mb-1 mt-4 block text-sm font-medium">Why is it being voided? (required)</label>
        <input
          id="void-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="h-11 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand"
          required
          autoFocus
        />
        {submit.error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{submit.error.message}</p>}
        <div className="mt-5 flex gap-2">
          <button type="submit" disabled={submit.isPending} className="h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60">
            Void calibration
          </button>
          <button type="button" onClick={onClose} className="h-11 rounded-lg border border-line px-5 font-medium hover:bg-brand-soft">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
