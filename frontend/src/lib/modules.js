import { ClipboardList, SprayCan, Thermometer, TriangleAlert } from 'lucide-react'

// The parts of the Achieve HACCP app. To add a module: add an entry here and its routes in App.jsx.
// forNight: whether the night login may use it. The night login only ever sees these.
export const modules = [
  {
    key: 'temperature',
    name: 'Temperature Logger',
    description: 'Coolroom and freezer temperatures, deliveries received and dispatch runs.',
    tables: 'HACCP Tables 9, 10 and 11',
    to: '/temperature',
    Icon: Thermometer,
    forNight: true,
  },
  {
    key: 'cleaning',
    name: 'Cleaning & Maintenance',
    description: 'Tick off the cleaning and maintenance tasks, with reminders for the monthly and quarterly ones, and the 6-monthly thermometer calibration.',
    tables: 'HACCP Tables 8 and 14',
    to: '/cleaning',
    Icon: SprayCan,
    forNight: false,
  },
  {
    key: 'ncr',
    name: 'Non-Conformance Reports',
    description: 'Record a problem with a product, follow it up with the manufacturer, attach photos and close it.',
    tables: 'HACCP Table 5',
    to: '/ncr',
    Icon: TriangleAlert,
    forNight: false,
  },
  {
    key: 'records',
    name: 'Records',
    description: 'Every saved record in one place: coolrooms and freezers, receiving, dispatch, calibration, cleaning and non-conformance reports.',
    tables: 'Tables 5, 8, 9, 10, 11 and 14',
    to: '/all-records',
    Icon: ClipboardList,
    forNight: false,
  },
]

export const modulesFor = (isAdmin) => (isAdmin ? modules : modules.filter((m) => m.forNight))
