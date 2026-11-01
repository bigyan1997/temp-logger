import { AlertTriangle, CheckCircle2, Clock, Circle } from 'lucide-react'
import { useState } from 'react'
import EntryRow from '../components/EntryRow.jsx'
import EntryShell from '../components/EntryShell.jsx'
import { formatDateTime, formatTime } from '../lib/format.js'
import { formatTemp, parseTemp } from '../lib/status.js'
import { useDay } from '../lib/useDay.js'
import { useEntryForm } from '../lib/useEntryForm.js'

const slotStates = {
  done: { label: 'Done', Icon: CheckCircle2, className: 'text-ok' },
  due: { label: 'Due now', Icon: Clock, className: 'text-near' },
  missed: { label: 'Missed', Icon: AlertTriangle, className: 'text-bad' },
  upcoming: { label: 'Not due yet', Icon: Circle, className: 'text-muted' },
}

// Pick the slot people most likely want: the first one still to do, else the next one coming.
function defaultSlot(slots) {
  const open = slots.find((s) => s.state === 'due' || s.state === 'missed')
  return open ?? slots.find((s) => s.state === 'upcoming') ?? slots[0]
}

function StorageScreen({ staffId, date }) {
  const { data: day } = useDay(date)
  const [chosen, setChosen] = useState(null)
  const slots = day?.storage ?? []
  const slot = slots.find((s) => s.slot === chosen) ?? defaultSlot(slots)

  const form = useEntryForm({
    endpoint: '/storage-readings/',
    staffId,
    buildBody: (key, entry) => ({ unit: Number(key.split('|')[1]), slot: key.split('|')[0], value: entry.temp }),
  })

  if (!day) return <p className="text-muted">Loading…</p>
  if (slots.length === 0) {
    return <p className="rounded-xl border border-line bg-surface p-4 text-muted">No storage readings are scheduled on this day.</p>
  }

  const keyFor = (unit) => `${slot.slot}|${unit.unit_id}`
  const toSave = slot.units.filter((u) => !u.reading && parseTemp(form.entryFor(keyFor(u)).temp) !== null)

  async function saveAll() {
    for (const unit of toSave) await form.save(keyFor(unit))
  }

  return (
    <>
      <div role="tablist" aria-label="Reading times" className="flex flex-wrap gap-2">
        {slots.map((s) => {
          const { label, Icon, className } = slotStates[s.state]
          const selected = s.slot === slot.slot
          return (
            <button
              key={s.slot}
              role="tab"
              aria-selected={selected}
              onClick={() => setChosen(s.slot)}
              className={`rounded-lg border px-4 py-2 text-left ${selected ? 'border-brand bg-brand-soft' : 'border-line bg-surface hover:bg-brand-soft'}`}
            >
              <span className="block font-semibold">{formatTime(s.slot)}</span>
              <span className={`flex items-center gap-1 text-sm ${className}`}>
                <Icon size={14} aria-hidden="true" /> {label}
              </span>
            </button>
          )
        })}
      </div>

      <p className="mb-2 mt-4 text-muted">{formatDateTime(slot.slot)}</p>
      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
        {slot.units.map((unit, index) => {
          const key = keyFor(unit)
          const entry = form.entryFor(key)
          return (
            <EntryRow
              key={key}
              kind="storage"
              label={unit.name}
              hint={`Limit ${formatTemp(unit.limit)} or colder`}
              limit={Number(unit.limit)}
              done={unit.reading && { summary: formatTemp(unit.reading.value), status: unit.reading.status, loggedBy: unit.reading.logged_by }}
              entry={entry}
              onChange={(patch) => form.setField(key, patch)}
              onSave={() => form.save(key)}
              onConfirm={() => form.confirm(key)}
              autoFocus={index === slot.units.findIndex((u) => !u.reading)}
            />
          )
        })}
      </ul>

      {toSave.length > 1 && (
        <button
          onClick={saveAll}
          className="mt-4 h-12 rounded-lg bg-brand px-6 font-semibold text-white hover:bg-brand-dark"
        >
          Save all {toSave.length} readings
        </button>
      )}
    </>
  )
}

export default function LogStorage() {
  return (
    <EntryShell
      title="Log storage temperatures"
      intro="Type each temperature and press Enter to save it. Coolrooms must be 5 °C or colder, freezers -15 °C or colder."
    >
      {(props) => <StorageScreen {...props} />}
    </EntryShell>
  )
}
