import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from '../api/client.js'
import CorrectiveFields, { correctiveBody, emptyCorrective } from './CorrectiveFields.jsx'

const inputClass =
  'h-11 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// Admin: cancel an entry and, optionally, save the corrected value in its place.
//   kind         storage | receiving | dispatch
//   endpoint     e.g. '/storage-readings/'
//   valueField   the field that holds the temperature: 'value' (storage) or 'temp'
//   entry        the row from the records table
export default function VoidDialog({ kind, endpoint, valueField, entry, title, onClose }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [newValue, setNewValue] = useState('')
  const [corrective, setCorrective] = useState(emptyCorrective)
  const [confirmed, setConfirmed] = useState(false)
  const [problem, setProblem] = useState(null) // {code, message, warnings}

  const submit = useMutation({
    mutationFn: () => {
      const replacement = newValue === '' ? undefined : {
        [valueField]: newValue,
        confirm_unusual: confirmed,
        ...(problem?.code === 'corrective_required' && corrective.action && { corrective: correctiveBody(corrective) }),
      }
      return api(`${endpoint}${entry.id}/void/`, { method: 'POST', body: { reason, ...(replacement && { replacement }) } })
    },
    onSuccess: () => {
      queryClient.invalidateQueries()
      onClose()
    },
    onError: (error) => {
      if (!(error instanceof ApiError)) throw error
      setProblem({ code: error.code, message: error.message, warnings: error.body?.warnings })
    },
  })

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-ink/40 p-4" role="dialog" aria-modal="true" aria-label="Void or correct entry">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit.mutate()
        }}
        className="w-full max-w-xl rounded-xl bg-surface p-5 shadow-lg"
      >
        <h2 className="text-lg font-semibold">Void or correct this entry</h2>
        <p className="mt-1 text-muted">{title}</p>
        <p className="mt-1 text-sm text-muted">
          The entry stays in the records, marked void, and the change is written to the audit log.
        </p>

        <label htmlFor="void-reason" className="mb-1 mt-4 block text-sm font-medium">
          Why is it being changed? (required)
        </label>
        <input id="void-reason" value={reason} onChange={(e) => setReason(e.target.value)} className={inputClass} required autoFocus />

        <label htmlFor="void-value" className="mb-1 mt-4 block text-sm font-medium">
          Correct temperature (leave empty to only void it)
        </label>
        <input
          id="void-value"
          value={newValue}
          onChange={(e) => {
            setNewValue(e.target.value)
            setProblem(null)
            setConfirmed(false)
          }}
          inputMode="decimal"
          className={`${inputClass} w-40`}
        />

        {problem?.code === 'needs_confirmation' && (
          <div role="alert" className="mt-3 rounded-lg border border-near/50 bg-amber-50 p-3 text-sm">
            <p className="font-medium text-near">Please check this value</p>
            <ul className="list-disc pl-5">{(problem.warnings ?? [problem.message]).map((w) => <li key={w}>{w}</li>)}</ul>
            <button
              type="button"
              onClick={() => {
                setConfirmed(true)
                setProblem(null)
              }}
              className="mt-2 h-9 rounded-lg bg-near px-3 font-semibold text-white"
            >
              Yes, that is correct
            </button>
          </div>
        )}

        {problem?.code === 'corrective_required' && (
          <div role="alert" className="mt-3 rounded-lg border border-bad/50 bg-red-50 p-3">
            <p className="mb-2 text-sm font-medium text-bad">The corrected value is out of limit. What was done about it?</p>
            <CorrectiveFields kind={kind} value={corrective} onChange={setCorrective} />
          </div>
        )}

        {problem && !['needs_confirmation', 'corrective_required'].includes(problem.code) && (
          <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{problem.message}</p>
        )}

        <div className="mt-5 flex gap-2">
          <button
            type="submit"
            disabled={submit.isPending}
            className="h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
          >
            {newValue === '' ? 'Void entry' : 'Void and save correction'}
          </button>
          <button type="button" onClick={onClose} className="h-11 rounded-lg border border-line px-5 font-medium hover:bg-brand-soft">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
