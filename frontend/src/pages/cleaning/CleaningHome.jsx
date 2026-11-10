import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { api } from '../../api/client.js'
import EntryShell from '../../components/EntryShell.jsx'
import { formatDay } from '../../lib/format.js'
import { focusNext } from '../../lib/focusNext.js'

const NEXT_TASK = 'input[data-task]:not(:disabled)' // the tick boxes that can still be ticked

const inputClass =
  'h-10 w-full rounded-lg border border-line bg-surface px-3 text-base focus:border-brand focus:outline-2 focus:outline-brand'

// Day staff: tick what was done on a day (the paper Table 8), pick your name, press Save.
export default function CleaningHome() {
  return (
    <EntryShell
      title="Cleaning & maintenance"
    >
      {({ staffId, date }) => <TaskList key={date} staffId={staffId} date={date} />}
    </EntryShell>
  )
}

// A task done once a day is locked once it is ticked. One that can be done again (stock put away) never locks:
// each tick adds another time.
const isLocked = (task) => task.done && !task.repeatable

function statusText(task, workingDay) {
  if (task.repeatable && task.done) return `Done ${task.times.length} time${task.times.length === 1 ? '' : 's'} today. Tick to add another`
  if (task.done) return `Done by ${task.times[0].done_by}`
  if (task.due) return 'Due'
  if (task.last_done) return `Done on ${formatDay(task.last_done)}`
  return workingDay ? 'Not due' : 'No cleaning scheduled on weekends'
}

function TaskList({ staffId, date }) {
  const queryClient = useQueryClient()
  const [ticked, setTicked] = useState({}) // task id -> true
  const [notes, setNotes] = useState({}) // task id -> note
  const saveButton = useRef(null)

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

  // Enter ticks the task and moves on to the next one; after the last task it moves to the Save button.
  const enterOnTask = (event, task) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    setTicked({ ...ticked, [task.id]: true })
    if (!focusNext(event.currentTarget, NEXT_TASK)) saveButton.current?.focus()
  }
  // A note can have several lines, so Enter starts a new line. Ctrl+Enter (or Tab) moves on to the next task.
  const enterInNote = (event) => {
    if (event.key !== 'Enter' || !event.ctrlKey) return
    event.preventDefault()
    const box = event.currentTarget.closest('li').querySelector('input[data-task]')
    if (!focusNext(box, NEXT_TASK)) saveButton.current?.focus()
  }

  if (isLoading || !data) return <p className="text-muted">Loading…</p>

  const firstOpenId = data.tasks.find((task) => !task.done)?.id // the cursor starts here, ready for Enter
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
                checked={isLocked(task) || Boolean(ticked[task.id])}
                disabled={isLocked(task)}
                data-task
                autoFocus={task.id === firstOpenId}
                onKeyDown={(e) => enterOnTask(e, task)}
                onChange={(e) => setTicked({ ...ticked, [task.id]: e.target.checked })}
                className="size-6 accent-brand"
              />
              <span className="font-medium">{task.name}</span>
            </label>
            <span className="w-56 text-sm text-muted">
              {task.frequency !== 'daily' && <span className="mr-2 rounded bg-brand-soft px-1.5 py-0.5 text-xs text-brand-dark">{task.frequency_label}</span>}
              {statusText(task, data.working_day)}
            </span>
            {task.times.length > 0 && (
              <ul className="basis-full space-y-1.5 pl-9 text-sm">
                {task.times.map((time) => (
                  <li key={time.number}>
                    <p className="flex items-center gap-1.5 font-medium text-ok">
                      <CheckCircle2 size={16} aria-hidden="true" />
                      Done{task.repeatable && ` (time ${time.number})`} by {time.done_by} at {time.at}
                    </p>
                    {/* What was done, on its own line so it is easy to read */}
                    <p className={`whitespace-pre-line pl-5 ${time.note ? 'text-ink' : 'text-muted'}`}>{time.note || 'No note'}</p>
                  </li>
                ))}
              </ul>
            )}
            {ticked[task.id] && (
              <textarea
                value={notes[task.id] ?? ''}
                onChange={(e) => setNotes({ ...notes, [task.id]: e.target.value })}
                placeholder="Note (optional). Enter starts a new line; Ctrl+Enter moves on."
                aria-label={`Note for ${task.name}`}
                maxLength={300}
                rows={2}
                onKeyDown={enterInNote}
                className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-base focus:border-brand focus:outline-2 focus:outline-brand sm:w-96"
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
          ref={saveButton}
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
