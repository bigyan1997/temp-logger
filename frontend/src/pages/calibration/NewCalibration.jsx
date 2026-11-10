import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, FileDown, XOctagon } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.js'
import EntryShell from '../../components/EntryShell.jsx'
import { useActiveList } from '../../lib/useActiveList.js'
import { newId } from '../../lib/uuid.js'

const TOLERANCE = 1 // the HACCP plan: thermometers must be accurate to +/-1 °C
const inputClass =
  'h-12 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// "3.2" -> 3.2, "" or "abc" -> null.
function toNumber(text) {
  const value = text.trim() === '' ? null : Number(text)
  return Number.isNaN(value) ? null : value
}

const tenths = (value) => Math.round(value * 10) / 10
const withinMargin = (difference) => Math.abs(tenths(difference)) <= TOLERANCE
const signed = (value) => `${tenths(value) > 0 ? '+' : ''}${tenths(value).toFixed(1)} °C`

// The probe thermometer's ice-point check, then each coolroom and freezer gauge compared with the probe.
export default function NewCalibration() {
  return (
    <EntryShell
      title="New thermometer calibration"
      intro="Fill in the form like the paper Table 14. When you press Save it is recorded, a PDF is made, and a copy is saved to Drive."
    >
      {({ staffId, date }) => <CalibrationForm staffId={staffId} date={date} />}
    </EntryShell>
  )
}

function CalibrationForm({ staffId, date }) {
  const queryClient = useQueryClient()
  const { data: units = [] } = useActiveList('/units/')
  const [id] = useState(newId) // made here so a double click or retry saves once
  const [probe, setProbe] = useState('')
  const [probeComment, setProbeComment] = useState('')
  const [action, setAction] = useState('replaced')
  const [actionNotes, setActionNotes] = useState('')
  const [gauges, setGauges] = useState({}) // unit id -> { gauge, probe, comment }

  const reading = toNumber(probe)
  const failed = reading !== null && !withinMargin(reading)

  const gaugeFor = (unitId) => gauges[unitId] ?? { gauge: '', probe: '', comment: '' }
  const setGauge = (unitId, changes) => setGauges({ ...gauges, [unitId]: { ...gaugeFor(unitId), ...changes } })

  const save = useMutation({
    mutationFn: () =>
      api('/calibrations/', {
        method: 'POST',
        body: {
          id,
          date,
          recorded_by: staffId,
          probe_reading: reading,
          probe_comment: probeComment,
          ...(failed && { action, action_notes: actionNotes }),
          gauges: units
            .filter((unit) => toNumber(gaugeFor(unit.id).gauge) !== null && toNumber(gaugeFor(unit.id).probe) !== null)
            .map((unit) => ({
              unit: unit.id,
              gauge_reading: toNumber(gaugeFor(unit.id).gauge),
              probe_reading: toNumber(gaugeFor(unit.id).probe),
              comment: gaugeFor(unit.id).comment,
            })),
        },
      }),
    onSuccess: () => queryClient.invalidateQueries(),
  })

  if (save.data) return <Saved result={save.data} />

  const halfFilled = units.find((unit) => {
    const { gauge, probe: probeText } = gaugeFor(unit.id)
    return (toNumber(gauge) === null) !== (toNumber(probeText) === null)
  })
  const problem = !staffId
    ? 'Pick your name first.'
    : reading === null
      ? 'Type what the probe read in the iced water.'
      : halfFilled
        ? `${halfFilled.name}: fill in both readings, or leave both empty.`
        : null

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
      className="space-y-6"
    >
      <section className="rounded-xl border border-line bg-surface p-4">
        <h2 className="font-semibold">1. Probe thermometer: ice point check</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-muted">
          <li>Fill a cup with crushed ice or small ice cubes and add a little water (no more than 1/3 of the ice) to make a slurry.</li>
          <li>Put the probe in the centre of the cup so it touches the ice and water but not the base.</li>
          <li>Leave it for 5 to 10 minutes, then stir.</li>
          <li>Take the reading. An accurate thermometer reads 0 °C.</li>
        </ol>

        <div className="mt-4 flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="probe" className="mb-1 block text-sm font-medium">What the probe read (°C)</label>
            <input id="probe" value={probe} onChange={(e) => setProbe(e.target.value)} inputMode="decimal" autoFocus className={`${inputClass} w-40`} />
          </div>
          <div className="mb-3 min-w-48 text-sm" aria-live="polite">
            {reading === null ? (
              <span className="text-muted">Difference from 0 °C shows here.</span>
            ) : failed ? (
              <span className="inline-flex items-center gap-1 font-medium text-bad">
                <XOctagon size={16} aria-hidden="true" /> {signed(reading)}: outside the margin of error
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 font-medium text-ok">
                <CheckCircle2 size={16} aria-hidden="true" /> {signed(reading)}: within the margin of error
              </span>
            )}
          </div>
          <div className="min-w-64 flex-1">
            <label htmlFor="probe-comment" className="mb-1 block text-sm font-medium">Comments (optional)</label>
            <input id="probe-comment" value={probeComment} onChange={(e) => setProbeComment(e.target.value)} className={inputClass} />
          </div>
        </div>

        {reading !== null && !failed && reading !== 0 && (
          <p className="mt-3 text-sm text-muted">
            Within the margin, so keep using it. Put a sticker on it saying "{reading > 0 ? 'minus' : 'plus'} {Math.abs(tenths(reading)).toFixed(1)} °C from reading".
          </p>
        )}

        {failed && (
          <div role="alert" className="mt-4 rounded-lg border border-bad/50 bg-red-50 p-3">
            <p className="text-sm font-medium text-bad">More than 1 °C out: the thermometer must be replaced or repaired. What was done?</p>
            <div className="mt-2 flex flex-wrap gap-3">
              <select value={action} onChange={(e) => setAction(e.target.value)} aria-label="Action taken" className={`${inputClass} w-64`}>
                <option value="replaced">Thermometer replaced</option>
                <option value="repaired">Thermometer repaired</option>
              </select>
              <input
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                placeholder="Note: what was done (optional)"
                aria-label="Note: what was done"
                className={`${inputClass} min-w-64 flex-1`}
              />
            </div>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-line bg-surface p-4">
        <h2 className="font-semibold">2. Coolroom and freezer gauges (optional)</h2>
        <p className="mt-1 text-sm text-muted">
          Leave the calibrated probe switched on inside the unit, then type what the unit's own gauge shows and what the probe shows. Leave a unit empty if it was not checked.
        </p>
        <div className="mt-3 divide-y divide-line">
          {units.map((unit) => {
            const row = gaugeFor(unit.id)
            const gaugeValue = toNumber(row.gauge)
            const probeValue = toNumber(row.probe)
            const difference = gaugeValue !== null && probeValue !== null ? gaugeValue - probeValue : null
            const off = difference !== null && !withinMargin(difference)
            return (
              <div key={unit.id} className="flex flex-wrap items-end gap-3 py-3">
                <p className="w-28 pb-3 font-medium">{unit.name}</p>
                <div>
                  <label htmlFor={`gauge-${unit.id}`} className="mb-1 block text-sm">Gauge shows (°C)</label>
                  <input id={`gauge-${unit.id}`} value={row.gauge} onChange={(e) => setGauge(unit.id, { gauge: e.target.value })} inputMode="decimal" className={`${inputClass} w-28`} />
                </div>
                <div>
                  <label htmlFor={`probe-${unit.id}`} className="mb-1 block text-sm">Probe shows (°C)</label>
                  <input id={`probe-${unit.id}`} value={row.probe} onChange={(e) => setGauge(unit.id, { probe: e.target.value })} inputMode="decimal" className={`${inputClass} w-28`} />
                </div>
                <p className="w-24 pb-3 text-sm" aria-live="polite">
                  {difference === null ? <span className="text-muted">Difference</span> : off ? (
                    <span className="inline-flex items-center gap-1 font-medium text-near"><AlertTriangle size={14} aria-hidden="true" /> {signed(difference)}</span>
                  ) : (
                    <span className="font-medium">{signed(difference)}</span>
                  )}
                </p>
                <div className="min-w-48 flex-1">
                  <label htmlFor={`comment-${unit.id}`} className="mb-1 block text-sm">Comment (optional)</label>
                  <input id={`comment-${unit.id}`} value={row.comment} onChange={(e) => setGauge(unit.id, { comment: e.target.value })} className={inputClass} />
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {save.error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-bad">{save.error.message}</p>}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={save.isPending || Boolean(problem)}
          className="h-12 rounded-lg bg-brand px-6 text-base font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
        >
          {save.isPending ? 'Saving…' : 'Save calibration'}
        </button>
        {problem && <p className="text-sm text-muted">{problem}</p>}
      </div>
    </form>
  )
}

// What the person sees once it is saved: where the PDF copies went, and a download button.
function Saved({ result }) {
  const { saved, problems } = result.copies
  return (
    <div className="rounded-xl border border-ok/40 bg-green-50 p-5">
      <p className="flex items-center gap-2 text-lg font-semibold text-ok">
        <CheckCircle2 size={22} aria-hidden="true" /> Calibration saved
        {!result.passed && ' (outside the margin of error: action recorded)'}
      </p>
      {saved.length > 0 && (
        <ul className="mt-3 list-disc pl-5 text-sm">
          {saved.map((place) => <li key={place}>PDF copy saved to {place}</li>)}
        </ul>
      )}
      {problems.length > 0 && (
        <div role="alert" className="mt-3 rounded-lg border border-near/50 bg-amber-50 p-3 text-sm">
          <p className="font-medium text-near">The calibration is recorded, but not every copy could be saved:</p>
          <ul className="list-disc pl-5">{problems.map((text) => <li key={text}>{text}</li>)}</ul>
          <p className="mt-1">You can still download the PDF below and save it yourself.</p>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <a href={`/api/calibrations/${result.id}/pdf/`} target="_blank" rel="noreferrer" className="inline-flex h-11 items-center gap-2 rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-dark">
          <FileDown size={18} aria-hidden="true" /> Download PDF
        </a>
        <Link to="/calibration" className="inline-flex h-11 items-center rounded-lg border border-line bg-surface px-4 font-medium hover:bg-brand-soft">
          Back to calibrations
        </Link>
      </div>
    </div>
  )
}
