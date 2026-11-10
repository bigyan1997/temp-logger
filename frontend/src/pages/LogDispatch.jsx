import { Check, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import ClosedNotice from '../components/ClosedNotice.jsx'
import EntryRow from '../components/EntryRow.jsx'
import EntryShell from '../components/EntryShell.jsx'
import SaveAll from '../components/SaveAll.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { formatTemp, parseTemp, statusFor } from '../lib/status.js'
import { useDay } from '../lib/useDay.js'
import { useEntryForm } from '../lib/useEntryForm.js'
import { useReadingOptions } from '../lib/useReadingOptions.js'

const isTyping = (target) => ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName)

// Type the load temperature once, tap the runs that went out, Save. A run that is not tapped is not recorded:
// the sheet and PDF say "Run not used" for it by themselves.
// The screen is keyed by date in LogDispatch below, so a new day starts with a clean screen.
function DispatchScreen({ staffId, date }) {
  const { data: day } = useDay(date)
  const { data: options } = useReadingOptions()
  const [selected, setSelected] = useState([]) // ids of the runs that went out
  const [custom, setCustom] = useState([]) // of those, the ones with their own temperature
  const [shared, setShared] = useState('') // the load temperature

  const form = useEntryForm({
    endpoint: '/dispatch-readings/',
    staffId,
    buildBody: (runId, entry) => ({ run: Number(runId), date, temp: entry.temp }),
  })

  const runs = day?.dispatch ?? []
  const keyOf = (run) => String(run.run_id)
  const wentOut = runs.filter((run) => selected.includes(run.run_id) && !run.entry)
  const alreadyLogged = runs.filter((run) => run.entry)

  function toggle(run) {
    if (run.entry) return
    if (selected.includes(run.run_id)) {
      setSelected(selected.filter((id) => id !== run.run_id))
      setCustom(custom.filter((id) => id !== run.run_id))
    } else {
      setSelected([...selected, run.run_id])
      form.setField(keyOf(run), { temp: shared }) // starts with the load temperature
    }
  }

  function changeShared(text) {
    setShared(text)
    wentOut.filter((run) => !custom.includes(run.run_id)).forEach((run) => form.setField(keyOf(run), { temp: text }))
  }

  function giveOwnTemperature(run) {
    if (!custom.includes(run.run_id)) setCustom([...custom, run.run_id])
  }

  // Press a run's letter (when not typing in a box) to tap that run.
  useEffect(() => {
    function onKey(event) {
      if (isTyping(event.target) || event.ctrlKey || event.metaKey || event.altKey) return
      const run = runs.find((r) => r.code.toLowerCase() === event.key.toLowerCase())
      if (run && !run.entry) {
        event.preventDefault()
        toggle(run)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (!day || !options) return <p className="text-muted">Loading…</p>

  const limit = Number(options.limits.chilled_max)
  const sharedValue = parseTemp(shared)
  const toSave = wentOut.filter((run) => {
    const entry = form.entryFor(keyOf(run))
    return entry.phase !== 'saved' && parseTemp(entry.temp) !== null
  })
  const saveAll = () => form.saveAll(toSave.map(keyOf))

  return (
    <>
      {day.closed && (
        <ClosedNotice label={day.closed}>No dispatch today. You can still log a run that goes out.</ClosedNotice>
      )}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label htmlFor="load-temp" className="mb-1 block text-sm font-medium">
            Load temperature (°C)
          </label>
          <input
            id="load-temp"
            value={shared}
            onChange={(e) => changeShared(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                saveAll()
              }
            }}
            inputMode="decimal"
            autoComplete="off"
            autoFocus
            placeholder="°C"
            className="h-14 w-36 rounded-lg border border-line bg-surface px-3 text-right text-2xl font-semibold tabular-nums focus:border-brand focus:outline-2 focus:outline-brand"
          />
        </div>
        <div className="pb-3">{sharedValue !== null && <StatusBadge status={statusFor(sharedValue, limit)} />}</div>
      </div>
      {shared !== '' && sharedValue === null && <p className="mt-2 text-sm text-bad">Type a temperature like 4.5.</p>}

      <p className="mb-2 mt-6 text-sm font-medium">
        Which runs went out? <span className="font-normal text-muted">(tap them, or press the letter)</span>
      </p>
      <div className="flex flex-wrap gap-2">
        {runs.map((run) => {
          const on = selected.includes(run.run_id)
          const logged = Boolean(run.entry)
          return (
            <button
              key={run.run_id}
              onClick={() => toggle(run)}
              disabled={logged}
              aria-pressed={on || logged}
              title={logged ? 'Already logged today' : undefined}
              className={`flex h-12 min-w-12 items-center justify-center gap-1 rounded-lg border px-4 text-lg font-semibold ${
                logged
                  ? 'border-line bg-bg text-muted'
                  : on
                    ? 'border-brand bg-brand text-white'
                    : 'border-line bg-surface hover:border-brand hover:text-brand'
              }`}
            >
              {(on || logged) && <Check size={16} aria-hidden="true" />}
              {run.code}
            </button>
          )
        })}
      </div>

      {wentOut.length > 0 && (
        <ul className="mt-5 divide-y divide-line rounded-xl border border-line bg-surface">
          {wentOut.map((run) => {
            const key = keyOf(run)
            const entry = form.entryFor(key)
            const own = custom.includes(run.run_id)
            const value = parseTemp(entry.temp)

            // The simple row: the shared temperature. Anything needing attention shows the full row.
            if (!own && entry.phase === 'idle') {
              return (
                <li key={key} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <span className="w-48 font-medium">Run {run.code}</span>
                  <span className="text-lg font-semibold tabular-nums">{value === null ? '—' : formatTemp(value)}</span>
                  {value !== null && <StatusBadge status={statusFor(value, limit)} />}
                  <span className="ml-auto flex items-center gap-2">
                    <button
                      onClick={() => giveOwnTemperature(run)}
                      className="h-9 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft"
                    >
                      Different temperature
                    </button>
                    <button
                      onClick={() => toggle(run)}
                      aria-label={`Run ${run.code} did not go out`}
                      className="grid size-9 place-items-center rounded-lg border border-line hover:bg-brand-soft"
                    >
                      <X size={16} aria-hidden="true" />
                    </button>
                  </span>
                </li>
              )
            }
            return (
              <EntryRow
                key={key}
                kind="dispatch"
                label={`Run ${run.code}`}
                limit={limit}
                entry={entry}
                onChange={(patch) => {
                  if ('temp' in patch) giveOwnTemperature(run)
                  form.setField(key, patch)
                }}
                onSave={() => form.save(key)}
                onConfirm={() => form.confirm(key)}
                onEnter={saveAll}
                moveOnEnter
                saveButton={false}
                autoFocus={own && entry.phase === 'idle'}
              />
            )
          })}
        </ul>
      )}

      <SaveAll count={toSave.length} busy={form.isBusy} onSave={saveAll} />

      {alreadyLogged.length > 0 && (
        <>
          <p className="mb-2 mt-8 text-sm font-medium text-muted">Already logged today</p>
          <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
            {alreadyLogged.map((run) => (
              <EntryRow
                key={keyOf(run)}
                kind="dispatch"
                label={`Run ${run.code}`}
                limit={limit}
                done={{ summary: formatTemp(run.entry.temp), status: run.entry.status, loggedBy: run.entry.logged_by }}
                entry={form.entryFor(keyOf(run))}
                onChange={() => {}}
                onSave={() => {}}
                onConfirm={() => {}}
              />
            ))}
          </ul>
        </>
      )}
    </>
  )
}

export default function LogDispatch() {
  return (
    <EntryShell
      title="Log dispatch temperatures"
      intro="Type the load temperature, tap the runs that went out, then Save. Runs you don't tap show as Run not used on the sheet. Enter moves to the next run; Enter on the last one saves."
    >
      {(props) => <DispatchScreen key={props.date} {...props} />}
    </EntryShell>
  )
}
