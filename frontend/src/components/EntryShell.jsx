import { useState } from 'react'
import { todayInSydney } from '../lib/format.js'
import StaffPicker, { useStaffChoice } from './StaffPicker.jsx'

// The top of every entry screen: title, who is taking the readings, and which day.
// `children` is a function that receives { staffId, date } so the screen below can use them.
export default function EntryShell({ title, intro, children }) {
  const { staff, staffId, setStaffId } = useStaffChoice()
  const [date, setDate] = useState(todayInSydney)

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-1 max-w-prose text-muted">{intro}</p>

      <div className="mt-6 flex flex-wrap items-end gap-6 rounded-xl border border-line bg-surface p-4">
        <div className="w-64">
          <StaffPicker staff={staff} staffId={staffId} setStaffId={setStaffId} />
        </div>
        <div className="mb-4">
          <label htmlFor="entry-date" className="mb-1 block text-sm font-medium">
            Day
          </label>
          <input
            id="entry-date"
            type="date"
            value={date}
            max={todayInSydney()}
            onChange={(e) => e.target.value && setDate(e.target.value)}
            className="h-12 rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand"
          />
        </div>
      </div>

      <div className="mt-6">{children({ staffId, date })}</div>
    </div>
  )
}
