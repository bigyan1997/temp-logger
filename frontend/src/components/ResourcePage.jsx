import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client.js'
import ItemForm from './ItemForm.jsx'

const buttonClass = 'h-10 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft'

// A complete "list, add, edit, deactivate/reactivate" screen for one section (see sections.js).
export default function ResourcePage({ section }) {
  const { endpoint, activeKey } = section
  const queryClient = useQueryClient()

  // editing: null (closed), 'new', or the item being edited
  const [editing, setEditing] = useState(null)
  const [error, setError] = useState('')

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['admin-list', endpoint],
    queryFn: () => api(`${endpoint}?all=1`),
  })

  const afterChange = () => {
    queryClient.invalidateQueries() // other screens (e.g. the name picker) show the same lists
    setEditing(null)
    setError('')
  }

  const save = useMutation({
    mutationFn: (body) =>
      editing === 'new'
        ? api(endpoint, { method: 'POST', body })
        : api(`${endpoint}${editing.id}/`, { method: 'PATCH', body }),
    onSuccess: afterChange,
    onError: (err) => setError(err.message),
  })

  const toggleActive = useMutation({
    mutationFn: (item) => api(`${endpoint}${item.id}/`, { method: 'PATCH', body: { [activeKey]: !item[activeKey] } }),
    onSuccess: afterChange,
    onError: (err) => setError(err.message),
  })

  function open(target) {
    setError('')
    setEditing(target)
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">{section.label}</h1>
      <p className="mt-1 max-w-prose text-muted">{section.intro}</p>

      <div className="mt-6">
        {editing ? (
          <ItemForm
            key={editing === 'new' ? 'new' : editing.id}
            fields={section.fields}
            item={editing === 'new' ? null : editing}
            saving={save.isPending}
            error={error}
            onSave={save.mutate}
            onCancel={() => open(null)}
          />
        ) : (
          <button
            onClick={() => open('new')}
            className="inline-flex h-11 items-center gap-2 rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-dark"
          >
            <Plus size={18} aria-hidden="true" /> {section.addLabel}
          </button>
        )}
      </div>

      {!editing && error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">
          {error}
        </p>
      )}

      <ul className="mt-6 divide-y divide-line rounded-xl border border-line bg-surface">
        {isLoading && <li className="px-4 py-3 text-muted">Loading…</li>}
        {!isLoading && items.length === 0 && <li className="px-4 py-3 text-muted">{section.empty}</li>}
        {items.map((item) => {
          const active = item[activeKey]
          return (
            <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className={`truncate font-medium ${active ? '' : 'text-muted line-through'}`}>{section.title(item)}</p>
                <p className="truncate text-sm text-muted">
                  {[section.detail?.(item), !active && 'Deactivated'].filter(Boolean).join(' · ')}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button onClick={() => open(item)} className={buttonClass}>
                  Edit
                </button>
                <button onClick={() => toggleActive.mutate(item)} className={buttonClass}>
                  {active ? 'Deactivate' : 'Reactivate'}
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
