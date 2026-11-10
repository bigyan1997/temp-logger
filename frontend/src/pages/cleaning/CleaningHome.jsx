import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/client.js'
import EntryShell from '../../components/EntryShell.jsx'
import { formatDay } from '../../lib/format.js'

const inputClass =
  'h-10 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// Day staff: tick what was done on a day (the paper Table 8), pick your name, press Save.
export default function CleaningHome() {
  return (
    <EntryShell
      title="Cleaning & maintenance"
      intro="HACCP Table 8. Tick each task that was done, then press Save. A task that is already ticked for the day is locked; if one was ticked by mistake, void it on the Records page."
    >
      {({ staffId, date }) => <TaskList key={date} staffId={staffId} date={date} />}
    </EntryShell>
  )
}

// What to say about a task that is not ticked yet.
function statusText(task, workingDay) {
  if (task.done) return `Done by ${task.done_by}`
  if (task.due) return 'Due'
  if (task.last_done) return `Done on ${formatDay(task.last_done)}`
  return workingDay ? 'Not due' : 'No cleaning scheduled on weekends'
}

function TaskList({ staffId, date }) {
  const queryClient = useQueryClient()
  const [ticked, setTicked] = useState({}) // task id -> true
  const [notes, setNotes] = useState({}) // task id -> note

  const { data, isLoading } = useQuery({
    queryKey: ['cleaning-day', date],
    queryFn: () => api(`/cleaning-checks/day/?date=${date}`),
  })

  const save = useMutation({
    mutationFn: () =>
      api('/cleaning-checks/', {
        method: 'POST',
        body: {
          date,
          recorded_by: staffId,
          ticks: Object.keys(ticked).filter((id) => ticked[id]).map((id) => ({ task: Number(id), note: notes[id] ?? '' })),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries()
      setTicked({})
      setNotes({})
    },
  })

  if (isLoading || !data) return <p className="text-muted">Loading…</p>

  const count = Object.values(ticked).filter(Boolean).length
  const problem = !staffId ? 'Pick your name first.' : count === 0 ? 'Tick at least one task.' : null

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
    >
      <p className="mb-3 font-medium">{formatDay(date)}</p>
      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
        {data.tasks.map((task) => (
          <li key={task.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
            <label className="flex min-w-72 flex-1 items-center gap-3">
              <input
                type="checkbox"
                checked={task.done || Boolean(ticked[task.id])}
                disabled={task.done}
                onChange={(e) => setTicked({ ...ticked, [task.id]: e.target.checked })}
                className="size-6 accent-brand"
              />
              <span className="font-medium">{task.name}</span>
            </label>
            <span className="w-56 text-sm text-muted">
              {task.frequency !== 'daily' && <span className="mr-2 rounded bg-brand-soft px-1.5 py-0.5 text-xs text-brand-dark">{task.frequency_label}</span>}
              {statusText(task, data.working_day)}
            </span>
            {task.done && task.note && <span className="text-sm text-muted">Note: {task.note}</span>}
            {ticked[task.id] && (
              <input
                value={notes[task.id] ?? ''}
                onChange={(e) => setNotes({ ...notes, [task.id]: e.target.value })}
                placeholder="Note (optional)"
                aria-label={`Note for ${task.name}`}
                maxLength={300}
                className={`${inputClass} sm:w-72`}
              />
            )}
          </li>
        ))}
      </ul>

      {save.error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-bad">{save.error.message}</p>}
      {save.isSuccess && count === 0 && <p role="status" className="mt-3 text-sm font-medium text-ok">Saved.</p>}
      <div className="mt-4 flex items-center gap-4">
        <button
          type="submit"
          disabled={Boolean(problem) || save.isPending}
          className="h-12 rounded-lg bg-brand px-6 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
        >
          Save {count > 0 ? `${count} task${count === 1 ? '' : 's'}` : ''}
        </button>
        {problem && <span className="text-sm text-muted">{problem}</span>}
      </div>
    </form>
  )
}
