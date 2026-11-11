import { Navigate, NavLink, useParams } from 'react-router-dom'
import { useAuth } from '../../auth.jsx'
import ResourcePage from '../../components/ResourcePage.jsx'
import SentAlerts from '../../components/SentAlerts.jsx'
import { listSections, settingsSections } from './sections.js'

const linkClass = ({ isActive }) =>
  `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-brand text-white' : 'text-muted hover:bg-brand-soft hover:text-ink'
  }`

// Admin-only: the section list on the left (a scrolling row on phones), the chosen section beside it.
// `base` is the address the sections live under, e.g. '/settings'.
function SectionPages({ sections, base }) {
  const { isAdmin } = useAuth()
  const { section: path } = useParams()
  const section = sections.find((s) => s.path === path)

  if (!isAdmin) return <Navigate to="/temperature" replace />
  if (!section) return <Navigate to={`${base}/${sections[0].path}`} replace />

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:gap-10">
      <nav
        aria-label="Sections"
        className="-mx-4 flex gap-1 overflow-x-auto px-4 sm:-mx-8 sm:px-8 lg:mx-0 lg:w-56 lg:shrink-0 lg:flex-col lg:overflow-visible lg:px-0"
      >
        {sections.map((s) => (
          <NavLink key={s.path} to={`${base}/${s.path}`} className={linkClass}>
            {s.label}
          </NavLink>
        ))}
      </nav>

      <div className="min-w-0 flex-1 lg:max-w-4xl">
        <ResourcePage key={section.path} section={section} />
        {section.path === 'alerts' && <SentAlerts />}
      </div>
    </div>
  )
}

// Settings for the whole app (a card on the front page).
export default function Settings() {
  const { section } = useParams()
  // Old addresses: the Temperature Logger's lists used to be here too.
  if (listSections.some((s) => s.path === section)) return <Navigate to={`/lists/${section}`} replace />
  return <SectionPages sections={settingsSections} base="/settings" />
}

// The Temperature Logger's own lists (in its menu).
export function Lists() {
  return <SectionPages sections={listSections} base="/lists" />
}
