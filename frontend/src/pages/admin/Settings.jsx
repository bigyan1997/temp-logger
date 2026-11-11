import { Navigate, useParams } from 'react-router-dom'
import { useAuth } from '../../auth.jsx'
import ResourcePage from '../../components/ResourcePage.jsx'
import SentAlerts from '../../components/SentAlerts.jsx'
import { listSections, settingsSections } from './sections.js'

// Admin-only: the chosen section. The sections themselves are links in the left-hand menu (lib/menus.js).
// `base` is the address the sections live under, e.g. '/settings'.
function SectionPages({ sections, base }) {
  const { isAdmin } = useAuth()
  const { section: path } = useParams()
  const section = sections.find((s) => s.path === path)

  if (!isAdmin) return <Navigate to="/temperature" replace />
  if (!section) return <Navigate to={`${base}/${sections[0].path}`} replace />

  return (
    <div className="max-w-4xl">
      <ResourcePage key={section.path} section={section} />
      {section.path === 'alerts' && <SentAlerts />}
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
