import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client.js'

// Cancel a record that was saved by mistake (Calibration and Cleaning). It stays in the list, marked void,
// and the change is written to the audit log. `endpoint` is the record's void address, e.g. '/calibrations/5/void/'.
export default function VoidReasonDialog({ heading, title, endpoint, onClose }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const submit = useMutation({
    mutationFn: () => api(endpoint, { method: 'POST', body: { reason } }),
    onSuccess: () => {
      queryClient.invalidateQueries()
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-ink/40 p-4" role="dialog" aria-modal="true" aria-label={heading}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit.mutate()
        }}
        className="w-full max-w-lg rounded-xl bg-surface p-5 shadow-lg"
      >
        <h2 className="text-lg font-semibold">{heading}</h2>
        <p className="mt-1 text-muted">{title}</p>
        <p className="mt-1 text-sm text-muted">It stays in the list, marked void, and the change is written to the audit log.</p>
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
            Void
          </button>
          <button type="button" onClick={onClose} className="h-11 rounded-lg border border-line px-5 font-medium hover:bg-brand-soft">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
