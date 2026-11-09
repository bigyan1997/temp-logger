import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Circle, XOctagon } from 'lucide-react'
import { api } from '../api/client.js'
import { formatDay } from '../lib/format.js'

// Every state has a shape and words as well as a colour.
const states = {
  never: { Icon: Circle, className: 'border-line bg-surface text-muted' },
  ok: { Icon: CheckCircle2, className: 'border-ok/40 bg-green-50 text-ok' },
  due_soon: { Icon: AlertTriangle, className: 'border-near/50 bg-amber-50 text-near' },
  overdue: { Icon: XOctagon, className: 'border-bad/50 bg-red-50 text-bad' },
}

// `enabled` is false for the night login, which may not see calibration.
export function useCalibrationDue(enabled = true) {
  return useQuery({
    queryKey: ['calibration-due'],
    queryFn: () => api('/calibrations/due/'),
    refetchInterval: 60_000,
    enabled,
  })
}

// The same sentence is used on the front page and on the Calibration home.
export function dueSentence({ state, due, days_left: daysLeft }) {
  if (state === 'never') return 'No thermometer calibration has been recorded yet.'
  const when = formatDay(due)
  if (state === 'overdue') return `Thermometer calibration is OVERDUE. It was due on ${when}.`
  if (state === 'due_soon') {
    const left = daysLeft === 0 ? 'today' : `in ${daysLeft} day${daysLeft === 1 ? '' : 's'}`
    return `Thermometer calibration is due ${left} (${when}).`
  }
  return `Next thermometer calibration is due on ${when}.`
}

export default function CalibrationStatus({ children }) {
  const { data } = useCalibrationDue()
  if (!data) return null
  const { Icon, className } = states[data.state]
  return (
    <div role="status" className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${className}`}>
      <p className="flex items-center gap-2 font-medium">
        <Icon size={20} aria-hidden="true" /> {dueSentence(data)}
      </p>
      {children}
    </div>
  )
}
