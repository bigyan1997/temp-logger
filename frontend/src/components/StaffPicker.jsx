import { useQuery } from '@tanstack/react-query'
import { UserRound } from 'lucide-react'
import { useEffect, useSyncExternalStore } from 'react'
import { api } from '../api/client.js'

const KEY = 'tl.staffId'
const CHANGED = 'tl:staff-changed'

export function useStaffList() {
  return useQuery({ queryKey: ['staff'], queryFn: () => api('/staff/') })
}

// The chosen person is kept here (and in localStorage) so the top bar and the entry screens always agree.
let chosenId = ''
try {
  chosenId = localStorage.getItem(KEY) || ''
} catch {
  /* private mode: just don't remember */
}

const subscribe = (onChange) => {
  window.addEventListener(CHANGED, onChange)
  return () => window.removeEventListener(CHANGED, onChange)
}

function setChosenId(id) {
  chosenId = id
  try {
    localStorage.setItem(KEY, id)
  } catch {
    /* private mode: just don't remember */
  }
  window.dispatchEvent(new Event(CHANGED))
}

// Remembers the last person picked on this computer, but only if they are still on the list.
export function useStaffChoice() {
  const { data: staff = [] } = useStaffList()
  const staffId = useSyncExternalStore(subscribe, () => chosenId)

  useEffect(() => {
    if (staffId && staff.length && !staff.some((s) => String(s.id) === String(staffId))) {
      setChosenId('')
    }
  }, [staff, staffId])

  return { staff, staffId, setStaffId: setChosenId }
}

// "Who is taking this reading?" Required on every entry form.
export default function StaffPicker({ staffId, setStaffId, staff }) {
  return (
    <div className="mb-4">
      <label htmlFor="staff" className="mb-1 flex items-center gap-2 text-sm font-medium">
        <UserRound size={16} aria-hidden="true" /> Your name
      </label>
      <select
        id="staff"
        value={staffId}
        onChange={(e) => setStaffId(e.target.value)}
        required
        className="h-12 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand"
      >
        <option value="" disabled>
          Choose your name…
        </option>
        {staff.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
      {staff.length === 0 && (
        <p className="mt-1 text-sm text-muted">No names yet. Ask the admin to add you under Staff names.</p>
      )}
    </div>
  )
}
