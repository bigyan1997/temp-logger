import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client.js'
import { formatDateTime } from '../lib/format.js'
import { AllClear, Panel } from './Panel.jsx'
import { useStaffList } from './StaffPicker.jsx'

const REFRESH_EVERY_MS = 60_000
const inputClass =
  'h-11 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// Out-of-limit readings waiting for a manager's approval. Used by the admin dashboard and the night home page.
// The logins are shared, so the manager picks their own name. If they took the reading themselves,
// they must also say why they are signing it off.
export default function SignOffPanel() {
  const queryClient = useQueryClient()
  const { data: staff = [] } = useStaffList()
  const managers = staff.filter((person) => person.can_sign_off)

  const [managerId, setManagerId] = useState('')
  const [notes, setNotes] = useState({}) // action id -> note

  const { data: waiting } = useQuery({
    queryKey: ['unsigned-actions'],
    queryFn: () => api('/corrective-actions/?unsigned=1'),
    refetchInterval: REFRESH_EVERY_MS,
  })
  const actions = waiting?.results ?? []

  const signOff = useMutation({
    mutationFn: (action) =>
      api(`/corrective-actions/${action.id}/signoff/`, {
        method: 'POST',
        body: { staff: Number(managerId), note: notes[action.id] ?? '' },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['unsigned-actions'] })
    },
  })

  return (
    <Panel title="Waiting for sign-off" count={actions.length}>
      {actions.length === 0 && <AllClear>Nothing to sign off.</AllClear>}

      {actions.length > 0 && (
        <div className="border-b border-line px-4 py-3">
          <label htmlFor="manager" className="mb-1 block text-sm font-medium">
            Signing off as
          </label>
          <select id="manager" value={managerId} onChange={(e) => setManagerId(e.target.value)} className={inputClass}>
            <option value="" disabled>
              Choose your name…
            </option>
            {managers.map((person) => (
              <option key={person.id} value={person.id}>
                {person.name}
              </option>
            ))}
          </select>
          {managers.length === 0 && (
            <p className="mt-1 text-sm text-muted">
              No managers yet. Under Settings, Staff names, tick "Manager" for the people who can sign off.
            </p>
          )}
        </div>
      )}

      {signOff.isError && (
        <p role="alert" className="px-4 pt-3 text-sm text-bad">
          {signOff.error.message}
        </p>
      )}

      <ul className="divide-y divide-line">
        {actions.map((a) => {
          const ownEntry = managerId !== '' && Number(managerId) === a.logged_by_id
          return (
            <li key={a.id} className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{a.summary}</p>
                  <p className="truncate text-sm text-muted">
                    {a.action_label} · {formatDateTime(a.created_at)} · Logged by {a.logged_by_name}
                    {a.notes && ` · ${a.notes}`}
                  </p>
                </div>
                <button
                  onClick={() => signOff.mutate(a)}
                  disabled={signOff.isPending || !managerId || (ownEntry && !(notes[a.id] ?? '').trim())}
                  title={managerId ? undefined : 'Choose your name first'}
                  className="h-10 shrink-0 rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
                >
                  Sign off
                </button>
              </div>
              {ownEntry && (
                <div className="mt-2">
                  <label htmlFor={`note-${a.id}`} className="mb-1 block text-sm font-medium text-near">
                    You took this reading. Why are you signing it off yourself?
                  </label>
                  <input
                    id={`note-${a.id}`}
                    value={notes[a.id] ?? ''}
                    onChange={(e) => setNotes({ ...notes, [a.id]: e.target.value })}
                    maxLength={500}
                    placeholder="e.g. Only manager on shift; rechecked twice"
                    className={inputClass}
                  />
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </Panel>
  )
}
