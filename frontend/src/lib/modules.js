import { ClipboardList, Gauge, SprayCan, Thermometer } from 'lucide-react'

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
    key: 'calibration',
    name: 'Calibration',
    description: 'The 6-monthly thermometer calibration form, with a PDF copy saved to Drive.',
    tables: 'HACCP Table 14',
    to: '/calibration',
    Icon: Gauge,
    forNight: false,
  },
  {
    key: 'cleaning',
    name: 'Cleaning & Maintenance',
    description: 'Tick off the daily, monthly and quarterly cleaning and maintenance tasks.',
    tables: 'HACCP Table 8',
    to: '/cleaning',
    Icon: SprayCan,
    forNight: false,
  },
  {
    key: 'records',
    name: 'Records',
    description: 'Every saved record in one place: coolrooms and freezers, receiving, dispatch, calibration and cleaning.',
    tables: 'Tables 8, 9, 10, 11 and 14',
    to: '/all-records',
    Icon: ClipboardList,
    forNight: false,
  },
]

export const modulesFor = (isAdmin) => (isAdmin ? modules : modules.filter((m) => m.forNight))
