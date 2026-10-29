import { useReadingOptions } from '../lib/useReadingOptions.js'

const inputClass =
  'h-11 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// "What did you do about it?" Shown when a reading is out of limit.
// `kind` is storage, receiving or dispatch. `value` is {action, notes, hours}.
export default function CorrectiveFields({ kind, value, onChange }) {
  const { data: options } = useReadingOptions()
  const choices = options?.corrective_actions[kind] ?? []
  const set = (patch) => onChange({ ...value, ...patch })

  return (
    <div className="grid gap-3 sm:grid-cols-[2fr_2fr_1fr]">
      <div>
        <label className="mb-1 block text-sm font-medium">What was done about it?</label>
        <select value={value.action} onChange={(e) => set({ action: e.target.value })} className={inputClass} required>
          <option value="" disabled>
            Choose an action…
          </option>
          {choices.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium">Notes (optional)</label>
        <input value={value.notes} onChange={(e) => set({ notes: e.target.value })} className={inputClass} />
      </div>
      {kind === 'storage' && (
        <div>
          <label className="mb-1 block text-sm font-medium">Hours too warm</label>
          <input
            value={value.hours}
            onChange={(e) => set({ hours: e.target.value })}
            inputMode="decimal"
            placeholder="e.g. 1.5"
            aria-invalid={!isHoursValid(value.hours)}
            className={inputClass}
          />
          {!isHoursValid(value.hours) && <p className="mt-1 text-sm text-bad">Type a number like 2 or 1.5.</p>}
        </div>
      )}
    </div>
  )
}

export const emptyCorrective = { action: '', notes: '', hours: '' }

// An action must be chosen, and "hours too warm" (optional) must be a number like 2 or 1.5.
export const isHoursValid = (hours) => hours === '' || /^\d{1,2}(\.\d)?$/.test(hours.trim())
export const isCorrectiveValid = (value) => Boolean(value.action) && isHoursValid(value.hours)

// The shape the API expects.
export function correctiveBody({ action, notes, hours }) {
  return { action, notes, ...(hours.trim() !== '' && { hours_above_limit: hours.trim() }) }
}
