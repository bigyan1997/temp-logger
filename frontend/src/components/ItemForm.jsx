import { useState } from 'react'

const inputClass =
  'h-12 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// Fields to show: when editing, skip the ones that can only be set at creation.
function visibleFields(fields, isNew) {
  return fields.filter((field) => isNew || !field.createOnly)
}

function startingValues(fields, item) {
  return Object.fromEntries(fields.map((f) => [f.name, item?.[f.name] ?? (f.type === 'select' ? f.options[0].value : f.type === 'checkbox' ? false : '')]))
}

// Add / edit form for one list item, driven by the section's field list.
export default function ItemForm({ fields, item, saving, error, onSave, onCancel }) {
  const isNew = !item
  const shown = visibleFields(fields, isNew)
  const [values, setValues] = useState(() => startingValues(shown, item))

  function submit(event) {
    event.preventDefault()
    const body = { ...values }
    for (const field of shown) {
      if (field.optionalOnEdit && !isNew && body[field.name] === '') delete body[field.name]
    }
    onSave(body)
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-line bg-surface p-4">
      <div className="grid gap-4">
        {shown.map((field) => {
          const id = `field-${field.name}`
          const required = field.required && !(field.optionalOnEdit && !isNew)
          return (
            <div key={field.name}>
              {field.type !== 'checkbox' && (
                <label htmlFor={id} className="mb-1 block text-sm font-medium">
                  {field.label}
                </label>
              )}
              {field.type === 'checkbox' ? (
                <label htmlFor={id} className="flex items-center gap-3 text-sm font-medium">
                  <input
                    id={id}
                    type="checkbox"
                    checked={values[field.name]}
                    onChange={(e) => setValues({ ...values, [field.name]: e.target.checked })}
                    className="size-5 accent-brand"
                  />
                  {field.label}
                </label>
              ) : field.type === 'select' ? (
                <select
                  id={id}
                  value={values[field.name]}
                  onChange={(e) => setValues({ ...values, [field.name]: e.target.value })}
                  className={inputClass}
                >
                  {field.options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id={id}
                  type={field.type}
                  step={field.type === 'number' ? '0.1' : undefined}
                  inputMode={field.type === 'number' ? 'decimal' : undefined}
                  autoComplete={field.type === 'password' ? 'new-password' : 'off'}
                  value={values[field.name]}
                  onChange={(e) => setValues({ ...values, [field.name]: e.target.value })}
                  required={required}
                  className={inputClass}
                />
              )}
              {field.help && <p className="mt-1 text-sm text-muted">{field.help}</p>}
            </div>
          )
        })}
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">
          {error}
        </p>
      )}

      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="h-11 rounded-lg border border-line px-5 font-medium hover:bg-brand-soft"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
