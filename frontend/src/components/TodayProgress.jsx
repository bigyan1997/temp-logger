import { CheckCircle2 } from 'lucide-react'

// One bar: how much of today's logging is done. `total` is null when there is no fixed number (dispatch).
function ProgressCard({ title, done, total, unit }) {
  const complete = total !== null && total > 0 && done >= total
  const percent = total ? Math.min(100, Math.round((done / total) * 100)) : 0

  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <p className="text-sm font-medium text-muted">{title}</p>
      <p className="mt-1 flex items-baseline gap-2">
        <span className="text-3xl font-semibold tabular-nums">{done}</span>
        <span className="text-muted">{total === null ? `${unit} logged` : `of ${total} ${unit}`}</span>
      </p>
      {total !== null && (
        <div className="mt-3 flex items-center gap-2">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-brand-soft" aria-hidden="true">
            <div className="h-full rounded-full bg-brand" style={{ width: `${percent}%` }} />
          </div>
          <span className="flex w-24 items-center justify-end gap-1 text-sm text-muted">
            {complete ? (
              <>
                <CheckCircle2 size={14} className="text-ok" aria-hidden="true" /> Done
              </>
            ) : (
              `${percent}%`
            )}
          </span>
        </div>
      )}
    </div>
  )
}

// Today's logging at a glance: storage readings, supplier checks and dispatch runs.
export default function TodayProgress({ today }) {
  return (
    <section aria-label="Today's logging">
      <h2 className="mb-2 font-semibold">Today so far</h2>
      <div className="grid gap-4 sm:grid-cols-3">
        <ProgressCard title="Storage readings" done={today.storage.done} total={today.storage.total} unit="readings" />
        <ProgressCard title="Deliveries received" done={today.receiving.done} total={today.receiving.total} unit="suppliers" />
        <ProgressCard title="Dispatch" done={today.dispatch.done} total={null} unit="runs" />
      </div>
    </section>
  )
}
