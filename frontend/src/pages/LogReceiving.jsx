import EntryRow from '../components/EntryRow.jsx'
import EntryShell from '../components/EntryShell.jsx'
import SaveAll from '../components/SaveAll.jsx'
import { formatTemp, parseTemp } from '../lib/status.js'
import { useDay } from '../lib/useDay.js'
import { useEntryForm } from '../lib/useEntryForm.js'
import { useReadingOptions } from '../lib/useReadingOptions.js'

function ReceivingScreen({ staffId, date }) {
  const { data: day } = useDay(date)
  const { data: options } = useReadingOptions()

  const form = useEntryForm({
    endpoint: '/receiving-checks/',
    staffId,
    buildBody: (supplierId, entry) => ({
      supplier: Number(supplierId),
      date,
      no_delivery: entry.noDelivery,
      product_type: entry.productType,
      packaging_ok: entry.packagingOk,
      ...(!entry.noDelivery && { temp: entry.temp }),
    }),
  })

  if (!day || !options) return <p className="text-muted">Loading…</p>

  const chilledLimit = Number(options.limits.chilled_max)
  const frozenLimit = Number(options.limits.frozen_max)
  const limitFor = (entry) => (entry.noDelivery ? null : entry.productType === 'frozen' ? frozenLimit : chilledLimit)
  const hintFor = (entry) =>
    entry.productType === 'frozen' ? `Frozen: ${formatTemp(frozenLimit)} or colder` : `Chilled: ${formatTemp(chilledLimit)} or colder`

  const firstOpen = day.receiving.findIndex((s) => !s.entry)

  // Rows with something typed (or "No delivery" ticked) that are not saved yet.
  const toSave = day.receiving
    .map((supplier) => String(supplier.supplier_id))
    .filter((key, index) => {
      const entry = form.entryFor(key)
      const filledIn = entry.noDelivery || parseTemp(entry.temp) !== null
      return !day.receiving[index].entry && entry.phase !== 'saved' && filledIn
    })
  const saveAll = () => form.saveAll(toSave)

  return (
    <>
      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
        {day.receiving.map((supplier, index) => {
          const key = String(supplier.supplier_id)
          const entry = form.entryFor(key)
          const logged = supplier.entry
          return (
            <EntryRow
              key={key}
              kind="receiving"
              receiving
              label={supplier.name}
              hint={hintFor(entry)}
              limit={limitFor(entry)}
              done={logged && {
                summary: logged.no_delivery ? 'No delivery' : formatTemp(logged.temp),
                status: logged.no_delivery ? 'none' : logged.status,
              }}
              entry={entry}
              onChange={(patch) => form.setField(key, patch)}
              onSave={() => form.save(key)}
              onConfirm={() => form.confirm(key)}
              onEnter={saveAll}
              saveButton={false}
              autoFocus={index === firstOpen}
            />
          )
        })}
      </ul>
      <SaveAll count={toSave.length} busy={form.isBusy} onSave={saveAll} />
    </>
  )
}

export default function LogReceiving() {
  return (
    <EntryShell
      title="Log deliveries received"
      intro="Check the temperature of each delivery when it arrives. Chilled must be 5 °C or colder, frozen -15 °C or colder. Tick No delivery if nothing came."
    >
      {(props) => <ReceivingScreen key={props.date} {...props} />}
    </EntryShell>
  )
}
