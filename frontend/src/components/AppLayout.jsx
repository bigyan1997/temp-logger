import { Home, LogOut, Settings, Thermometer } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth.jsx'

const navClass = ({ isActive }) =>
  `inline-flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium ${
    isActive ? 'bg-brand-soft text-brand-dark' : 'text-muted hover:bg-brand-soft hover:text-ink'
  }`

// The frame around every signed-in page: a full-width top bar and the page below it.
export default function AppLayout() {
  const { user, logout, isAdmin } = useAuth()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line bg-surface">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-8">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-lg bg-brand text-white">
              <Thermometer size={20} aria-hidden="true" />
            </span>
            <span className="font-semibold">Temperature Logger</span>
          </div>

          <nav aria-label="Main" className="flex gap-1">
            <NavLink to="/" end className={navClass}>
              <Home size={16} aria-hidden="true" /> Home
            </NavLink>
            {isAdmin && (
              <NavLink to="/settings" className={navClass}>
                <Settings size={16} aria-hidden="true" /> Settings
              </NavLink>
            )}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <div className="text-right leading-tight">
              <p className="text-sm font-medium">{user.display_name}</p>
              <p className="text-xs text-muted">{isAdmin ? 'Admin (day)' : 'Night shift'}</p>
            </div>
            <button
              onClick={logout}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft"
            >
              <LogOut size={16} aria-hidden="true" /> Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 px-4 py-6 sm:px-8 sm:py-8">
        <Outlet />
      </main>
    </div>
  )
}
