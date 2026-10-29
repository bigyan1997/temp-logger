import { CheckCircle2 } from 'lucide-react'
import { parseTemp, statusFor } from '../lib/status.js'
import CorrectiveFields, { isCorrectiveValid } from './CorrectiveFields.jsx'
import StatusBadge from './StatusBadge.jsx'

const inputClass =
  'h-11 rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// One line of an entry screen: what is being measured, a temperature box, and what happened.
//
//   label, hint     e.g. "Freezer" and "Limit -15 °C or colder"
//   done            the reading already saved for this row, or null
//   limit           the limit used for the live status while typing (null: no check, e.g. "no delivery")
//   entry, onChange the row's form state from useEntryForm
//   onSave, onConfirm
//   onEnter         what the Enter key does (default: save this row)
//   saveButton      false when the screen has one Save button for all its rows
//   kind            storage | receiving | dispatch
//   receiving       true to show the product type, packaging and "no delivery" fields
//   autoFocus       focus the temperature box when the screen opens
export default function EntryRow({ label, hint, done, limit, entry, onChange, onSave, onConfirm, onEnter = onSave, saveButton = true, kind, receiving, autoFocus }) {
  const value = parseTemp(entry.temp)
  const liveStatus = value !== null && limit !== null ? statusFor(value, limit) : 'none'
  const busy = entry.phase === 'saving'

  if (done) {
    return (
      <li className="flex flex-wrap items-center gap-3 px-4 py-3">
        <span className="w-48 font-medium">{label}</span>
        <span className="text-lg font-semibold tabular-nums">{done.summary}</span>
        <StatusBadge status={done.status} />
        <span className="ml-auto flex items-center gap-1 text-sm text-ok">
          <CheckCircle2 size={16} aria-hidden="true" /> Logged
        </span>
      </li>
    )
  }

  const saved = entry.phase === 'saved'
  if (saved) {
    return (
      <li className="flex flex-wrap items-center gap-3 px-4 py-3">
        <span className="w-48 font-medium">{label}</span>
        <span className="flex items-center gap-1 text-ok">
          <CheckCircle2 size={18} aria-hidden="true" /> Saved
        </span>
      </li>
    )
  }

  const submitOnEnter = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      onEnter()
    }
  }

  return (
    <li className="px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="w-48">
          <p className="font-medium">{label}</p>
          {hint && <p className="text-sm text-muted">{hint}</p>}
        </div>

        {receiving && (
          <>
            <select
              aria-label={`Product type for ${label}`}
              value={entry.productType}
              onChange={(e) => onChange({ productType: e.target.value })}
              disabled={entry.noDelivery}
              className={inputClass}
            >
              <option value="chilled">Chilled</option>
              <option value="frozen">Frozen</option>
              <option value="baked_pie">Freshly baked pies</option>
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={entry.noDelivery}
                onChange={(e) => onChange({ noDelivery: e.target.checked, temp: '' })}
                className="size-5 accent-brand"
              />
              No delivery
            </label>
          </>
        )}

        <input
          aria-label={`Temperature for ${label}`}
          value={entry.temp}
          onChange={(e) => onChange({ temp: e.target.value })}
          onKeyDown={submitOnEnter}
          disabled={busy || entry.noDelivery}
          inputMode="decimal"
          autoComplete="off"
          autoFocus={autoFocus}
          placeholder="°C"
          className={`${inputClass} w-28 text-right text-xl font-semibold tabular-nums`}
        />
        <span className="w-32">
          {entry.noDelivery ? null : <StatusBadge status={liveStatus} />}
        </span>

        {receiving && (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={entry.packagingOk}
              onChange={(e) => onChange({ packagingOk: e.target.checked })}
              className="size-5 accent-brand"
            />
            Packaging OK
          </label>
        )}

        <input
          aria-label={`Note for ${label}`}
          value={entry.note}
          onChange={(e) => onChange({ note: e.target.value })}
          onKeyDown={submitOnEnter}
          placeholder="Note (optional)"
          className={`${inputClass} min-w-40 flex-1`}
        />

        {saveButton && (
          <button
            onClick={() => onSave()}
            disabled={busy || (!entry.noDelivery && value === null)}
            className="h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {busy ? 'Saving…' : 'Save'}
          </button>
        )}
      </div>

      {entry.temp !== '' && value === null && (
        <p className="mt-2 text-sm text-bad">Type a temperature like 4.5 or -18.2.</p>
      )}

      {entry.phase === 'needs_confirm' && (
        <div role="alert" className="mt-3 rounded-lg border border-near/50 bg-amber-50 p-3">
          <p className="font-medium text-near">Please check this value</p>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {entry.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <div className="mt-2 flex gap-2">
            <button onClick={onConfirm} className="h-10 rounded-lg bg-near px-4 text-sm font-semibold text-white">
              Yes, that is correct
            </button>
            <button
              onClick={() => onChange({ phase: 'idle', warnings: [] })}
              className="h-10 rounded-lg border border-line bg-surface px-4 text-sm font-medium"
            >
              Let me change it
            </button>
          </div>
        </div>
      )}

      {entry.phase === 'needs_corrective' && (
        <div role="alert" className="mt-3 rounded-lg border border-bad/50 bg-red-50 p-3">
          <p className="mb-2 font-medium text-bad">
            {receiving && entry.packagingOk === false && liveStatus !== 'out_of_limit'
              ? 'The packaging is not OK. What was done about it?'
              : 'This is out of limit. What was done about it?'}
          </p>
          <CorrectiveFields kind={kind} value={entry.corrective} onChange={(corrective) => onChange({ corrective })} />
          {entry.message && <p className="mt-2 text-sm text-bad">{entry.message}</p>}
          <button
            onClick={() => onSave()}
            disabled={busy || !isCorrectiveValid(entry.corrective)}
            className="mt-3 h-10 rounded-lg bg-bad px-4 text-sm font-semibold text-white disabled:opacity-50"
          >
            Save with this action
          </button>
        </div>
      )}

      {entry.phase === 'error' && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">
          {entry.message}
        </p>
      )}
    </li>
  )
}
