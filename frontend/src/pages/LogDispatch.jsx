import { useEffect, useState } from 'react'
import EntryRow from '../components/EntryRow.jsx'
import EntryShell from '../components/EntryShell.jsx'
import SaveAll from '../components/SaveAll.jsx'
import { formatTemp, parseTemp } from '../lib/status.js'
import { useDay } from '../lib/useDay.js'
import { useEntryForm } from '../lib/useEntryForm.js'
import { useReadingOptions } from '../lib/useReadingOptions.js'

const isTyping = (target) => ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName)

// The screen is keyed by date in LogDispatch below, so a new day starts with a clean screen.
function DispatchScreen({ staffId, date }) {
  const { data: day } = useDay(date)
  const { data: options } = useReadingOptions()
  const [added, setAdded] = useState([]) // runs the user added for this day (run ids)
  const [justAdded, setJustAdded] = useState(null) // the run to put the cursor in

  const form = useEntryForm({
    endpoint: '/dispatch-readings/',
    staffId,
    buildBody: (runId, entry) => ({ run: Number(runId), date, temp: entry.temp }),
  })

  const runs = day?.dispatch ?? []
  const isShown = (run) => run.entry || added.includes(run.run_id)

  // Press a run's letter (when not typing in a box) to add that run.
  useEffect(() => {
    function onKey(event) {
      if (isTyping(event.target) || event.ctrlKey || event.metaKey || event.altKey) return
      const run = runs.find((r) => r.code.toLowerCase() === event.key.toLowerCase())
      if (run && !isShown(run)) {
        event.preventDefault()
        addRun(run)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  function addRun(run) {
    setAdded((ids) => [...ids, run.run_id])
    setJustAdded(run.run_id)
  }

  if (!day || !options) return <p className="text-muted">Loading…</p>

  const limit = Number(options.limits.chilled_max)
  const shown = runs.filter(isShown)
  const notShown = runs.filter((run) => !isShown(run))
  const readyToSave = (run) => {
    const entry = form.entryFor(String(run.run_id))
    return !run.entry && entry.phase !== 'saved' && parseTemp(entry.temp) !== null
  }
  const toSave = shown.filter(readyToSave)
  const saveAll = () => form.saveAll(toSave.map((r) => String(r.run_id)))

  return (
    <>
      {notShown.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">Add a run that went out:</span>
          {notShown.map((run) => (
            <button
              key={run.run_id}
              onClick={() => addRun(run)}
              className="h-10 min-w-10 rounded-lg border border-line bg-surface px-3 font-semibold hover:border-brand hover:text-brand"
            >
              {run.code}
            </button>
          ))}
          <span className="text-sm text-muted">or press its letter on the keyboard</span>
        </div>
      )}

      {shown.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line p-6 text-muted">No runs added yet. Choose the runs that went out above.</p>
      ) : (
        <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
          {shown.map((run) => {
            const key = String(run.run_id)
            return (
              <EntryRow
                key={key}
                kind="dispatch"
                label={`Run ${run.code}`}
                hint={`Limit ${formatTemp(limit)} or colder`}
                limit={limit}
                done={run.entry && { summary: formatTemp(run.entry.temp), status: run.entry.status }}
                entry={form.entryFor(key)}
                onChange={(patch) => form.setField(key, patch)}
                onSave={() => form.save(key)}
                onConfirm={() => form.confirm(key)}
                onEnter={saveAll}
                saveButton={false}
                autoFocus={run.run_id === justAdded}
              />
            )
          })}
        </ul>
      )}

      <SaveAll count={toSave.length} busy={form.isBusy} onSave={saveAll} />
    </>
  )
}

export default function LogDispatch() {
  return (
    <EntryShell
      title="Log dispatch temperatures"
      intro="Add the runs that went out, then record the temperature of each load before it leaves. It must be 5 °C or colder."
    >
      {(props) => <DispatchScreen key={props.date} {...props} />}
    </EntryShell>
  )
}
