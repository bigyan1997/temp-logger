import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client.js'

// Delete a whole report (for one made by mistake or while testing). It asks for a reason, and the audit log keeps
// a line saying what was deleted. A plain mistake in a real report should be voided instead.
export default function DeleteReport({ report, onClose }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [reason, setReason] = useState('')
  const [sure, setSure] = useState(false)
  const remove = useMutation({
    mutationFn: () => api(`/non-conformances/${report.id}/delete/`, { method: 'POST', body: { reason } }),
    onSuccess: (result) => {
      queryClient.invalidateQueries()
      if (result.problems.length === 0) navigate('/ncr')
    },
  })
  const photoCount = report.photos.length
  const updateCount = report.updates.length

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-ink/40 p-4" role="dialog" aria-modal="true" aria-label="Delete this report">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          remove.mutate()
        }}
        className="w-full max-w-lg rounded-xl bg-surface p-5 shadow-lg"
      >
        <h2 className="text-lg font-semibold text-bad">Delete this report</h2>
        <p className="mt-1 text-muted">{report.number} · {report.product}</p>
        {remove.data ? (
          <>
            <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-near">
              The report is deleted, but: {remove.data.problems.join(' ')}
            </p>
            <button type="button" onClick={() => navigate('/ncr')} className="mt-5 h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark">Close</button>
          </>
        ) : (
          <>
            <p className="mt-2 text-sm">
              This removes the report{updateCount ? `, its ${updateCount} follow-up${updateCount === 1 ? '' : 's'}` : ''}{photoCount ? ` and its ${photoCount} photo${photoCount === 1 ? '' : 's'}` : ''} for good.
              The photos are removed from this computer and the report's Google Drive folder goes to Drive's Bin. The audit log keeps one line saying what was deleted and why.
              If it is a real report with a mistake in it, <strong>void</strong> it instead.
            </p>
            <label htmlFor="delete-reason" className="mb-1 mt-4 block text-sm font-medium">Why is it being deleted? (required)</label>
            <textarea
              id="delete-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              maxLength={300}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-base focus:border-brand focus:outline-2 focus:outline-brand"
              required
              autoFocus
            />
            <label className="mt-3 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} className="size-5 accent-brand" />
              Yes, delete this report for good
            </label>
            {remove.error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{remove.error.message}</p>}
            <div className="mt-5 flex gap-2">
              <button type="submit" disabled={!sure || reason.trim().length < 3 || remove.isPending} className="h-11 rounded-lg bg-bad px-5 font-semibold text-white hover:opacity-90 disabled:opacity-50">
                {remove.isPending ? 'Deleting…' : 'Delete report'}
              </button>
              <button type="button" onClick={onClose} className="h-11 rounded-lg border border-line px-5 font-medium hover:bg-brand-soft">Cancel</button>
            </div>
          </>
        )}
      </form>
    </div>
  )
}
