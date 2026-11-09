import { Thermometer } from 'lucide-react'

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
]

export const modulesFor = (isAdmin) => (isAdmin ? modules : modules.filter((m) => m.forNight))
