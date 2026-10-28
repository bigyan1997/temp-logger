import { Navigate, NavLink, useParams } from 'react-router-dom'
import { useAuth } from '../../auth.jsx'
import ResourcePage from '../../components/ResourcePage.jsx'
import { sections } from './sections.js'

const linkClass = ({ isActive }) =>
  `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-brand text-white' : 'text-muted hover:bg-brand-soft hover:text-ink'
  }`

// Admin-only settings: section list on the left (a scrolling row on phones), the chosen section beside it.
export default function Settings() {
  const { isAdmin } = useAuth()
  const { section: path } = useParams()
  const section = sections.find((s) => s.path === path)

  if (!isAdmin) return <Navigate to="/" replace />
  if (!section) return <Navigate to={`/settings/${sections[0].path}`} replace />

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:gap-10">
      <nav
        aria-label="Settings sections"
        className="-mx-4 flex gap-1 overflow-x-auto px-4 sm:-mx-8 sm:px-8 lg:mx-0 lg:w-56 lg:shrink-0 lg:flex-col lg:overflow-visible lg:px-0"
      >
        {sections.map((s) => (
          <NavLink key={s.path} to={`/settings/${s.path}`} className={linkClass}>
            {s.label}
          </NavLink>
        ))}
      </nav>

      <div className="min-w-0 flex-1 lg:max-w-4xl">
        <ResourcePage key={section.path} section={section} />
      </div>
    </div>
  )
}
