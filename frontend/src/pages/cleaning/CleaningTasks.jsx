import ResourcePage from '../../components/ResourcePage.jsx'

// The tasks on the paper Table 8: add a new van, rename one, or deactivate one that is no longer done.
const section = {
  label: 'Cleaning tasks',
  endpoint: '/cleaning-tasks/',
  intro:
    'The tasks ticked on the Cleaning screen, one for each column of the paper Table 8. "Every working day" tasks are due Monday to Friday; monthly and quarterly ones are due until they are done in that month or quarter. A task that has been ticked cannot be deleted: deactivate it, and its old ticks keep their name.',
  addLabel: 'Add a task',
  empty: 'No tasks yet.',
  activeKey: 'active',
  title: (item) => item.name,
  detail: (item) => [item.frequency_label, item.notify && 'sends reminders', item.repeatable && 'can be done more than once a day'].filter(Boolean).join(', '),
  fields: [
    { name: 'name', label: 'Task', type: 'text', required: true },
    {
      name: 'frequency',
      label: 'How often',
      type: 'select',
      required: true,
      options: [
        { value: 'daily', label: 'Every working day' },
        { value: 'monthly', label: 'Once a month' },
        { value: 'quarterly', label: 'Once a quarter' },
      ],
    },
    {
      name: 'notify',
      label: 'Send reminders',
      type: 'checkbox',
      help: 'For a monthly or quarterly task: show a notice and email a reminder when it is due, and again every week until it is ticked off.',
    },
    {
      name: 'repeatable',
      label: 'Can be done more than once a day',
      type: 'checkbox',
      help: 'Tick for a task like stock put away, done after every delivery. Each time it is ticked is saved as another entry, with its own name, time and note.',
    },
  ],
}

export default function CleaningTasks() {
  return (
    <div className="max-w-4xl">
      <ResourcePage section={section} />
    </div>
  )
}
