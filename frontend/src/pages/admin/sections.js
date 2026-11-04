// What each settings page manages. ResourcePage turns one of these into a
// working "list, add, edit, deactivate" screen, so adding a new list is just
// adding an entry here.
//
// field.type: text | email | number | select | password
// field.createOnly: only asked when adding (cannot be changed later)
// field.optionalOnEdit: left blank when editing means "keep what it is now"

import { formatDay } from '../../lib/format.js'

export const sections = [
  {
    path: 'staff',
    label: 'Staff names',
    endpoint: '/staff/',
    intro:
      'People who take readings. Staff pick their name on every entry, so auditors see who did it. Tick "Day and night logins" for anyone who works on both; everyone else only appears on the night login.',
    addLabel: 'Add a name',
    empty: 'No names yet. Add the first one.',
    activeKey: 'active',
    title: (item) => item.name,
    detail: (item) => (item.both_logins ? 'Day and night logins' : 'Night login only'),
    fields: [
      { name: 'name', label: 'Full name', type: 'text', required: true },
      {
        name: 'both_logins',
        label: 'Day and night logins',
        type: 'checkbox',
        help: 'Tick to offer this name on both the day and night logins. Unticked names appear only on the night login.',
      },
    ],
  },
  {
    path: 'units',
    label: 'Storage units',
    endpoint: '/units/',
    intro:
      'Coolrooms and freezers that are checked twice a day. The limit is the warmest temperature that is still allowed.',
    addLabel: 'Add a unit',
    empty: 'No units yet.',
    activeKey: 'active',
    title: (item) => item.name,
    detail: (item) => `${item.kind === 'frozen' ? 'Frozen' : 'Chilled'}, limit ${item.max_temp} °C or colder`,
    fields: [
      { name: 'name', label: 'Name', type: 'text', required: true },
      {
        name: 'kind',
        label: 'Type',
        type: 'select',
        required: true,
        options: [
          { value: 'chilled', label: 'Chilled' },
          { value: 'frozen', label: 'Frozen' },
        ],
      },
      {
        name: 'max_temp',
        label: 'Limit (°C)',
        type: 'number',
        required: true,
        help: 'The warmest allowed temperature, for example 5 or -15.',
      },
    ],
  },
  {
    path: 'suppliers',
    label: 'Suppliers',
    endpoint: '/suppliers/',
    intro: 'Suppliers whose deliveries are temperature-checked when they arrive.',
    addLabel: 'Add a supplier',
    empty: 'No suppliers yet.',
    activeKey: 'active',
    title: (item) => item.name,
    detail: (item) => (item.usually_frozen ? 'Usually frozen' : 'Usually chilled'),
    fields: [
      { name: 'name', label: 'Supplier name', type: 'text', required: true },
      {
        name: 'usually_frozen',
        label: 'Usually frozen',
        type: 'checkbox',
        help: 'Receiving starts on Frozen for this supplier. It can still be changed to Chilled on any delivery.',
      },
    ],
  },
  {
    path: 'runs',
    label: 'Delivery runs',
    endpoint: '/runs/',
    intro: 'Delivery runs whose temperature is logged at dispatch. There is no run F or I.',
    addLabel: 'Add a run',
    empty: 'No runs yet.',
    activeKey: 'active',
    title: (item) => `Run ${item.code}`,
    fields: [{ name: 'code', label: 'Run letter', type: 'text', required: true }],
  },
  {
    path: 'closed-days',
    label: 'Public holidays',
    endpoint: '/closed-days/',
    intro:
      'Days when nothing needs logging. On a closed day the daytime storage readings and the evening before are not due (no reminder emails, nothing shown as missed), and Receiving and Dispatch are skipped. That day\'s own evening storage reading is still due, because deliveries go out the next morning. say "Public holiday" instead of leaving a gap. Readings can still be logged on these days.',
    addLabel: 'Add a public holiday',
    empty: 'No public holidays yet.',
    activeKey: 'active',
    title: (item) => formatDay(item.date),
    detail: (item) => item.label,
    fields: [
      { name: 'date', label: 'Date', type: 'date', required: true },
      {
        name: 'label',
        label: 'Name',
        type: 'text',
        help: 'Shown on the reports. Leave blank for "Public holiday", or write for example "Public holiday - Christmas Day".',
      },
    ],
  },
  {
    path: 'alerts',
    label: 'Alert emails',
    endpoint: '/alert-recipients/',
    intro:
      'Who is emailed when a storage reading is almost due, was missed, is out of limit, or a corrective action is still waiting for a manager. Deactivate an address to stop its emails.',
    addLabel: 'Add an email address',
    empty: 'No addresses yet. Add one to start getting alerts.',
    activeKey: 'active',
    title: (item) => item.email,
    fields: [{ name: 'email', label: 'Email address', type: 'email', required: true }],
  },
  {
    path: 'logins',
    label: 'Logins',
    endpoint: '/users/',
    intro:
      'Accounts that can sign in. Day staff use an Admin login; night staff use a Night login. Logins are never deleted; deactivate them instead.',
    addLabel: 'Add a login',
    empty: 'No logins yet.',
    activeKey: 'is_active',
    title: (item) => item.email,
    detail: (item) => (item.role === 'admin' ? 'Admin (day)' : 'Night'),
    fields: [
      { name: 'email', label: 'Email', type: 'email', required: true, createOnly: true },
      { name: 'first_name', label: 'Display name', type: 'text' },
      {
        name: 'role',
        label: 'Role',
        type: 'select',
        required: true,
        options: [
          { value: 'night', label: 'Night' },
          { value: 'admin', label: 'Admin (day)' },
        ],
      },
      {
        name: 'password',
        label: 'Password',
        type: 'password',
        required: true,
        optionalOnEdit: true,
        help: 'When editing, leave blank to keep the current password.',
      },
    ],
  },
]
