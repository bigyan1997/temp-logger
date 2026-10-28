import { useQuery } from '@tanstack/react-query'
import { UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const KEY = 'tl.staffId'

export function useStaffList() {
  return useQuery({ queryKey: ['staff'], queryFn: () => api('/staff/') })
}

// Remembers the last person picked on this phone, but only if they are still on the list.
export function useStaffChoice() {
  const { data: staff = [] } = useStaffList()
  const [staffId, setStaffIdState] = useState(() => {
    try {
      return localStorage.getItem(KEY) || ''
    } catch {
      return ''
    }
  })

  useEffect(() => {
    if (staffId && staff.length && !staff.some((s) => String(s.id) === String(staffId))) {
      setStaffIdState('')
    }
  }, [staff, staffId])

  function setStaffId(id) {
    setStaffIdState(id)
    try {
      localStorage.setItem(KEY, id)
    } catch {
      /* private mode: just don't remember */
    }
  }

  return { staff, staffId, setStaffId }
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
