import { LayoutGrid, LogOut, UserRound } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { modulesFor } from '../lib/modules.js'
import { useStaffChoice } from './StaffPicker.jsx'
import UpdateBanner from './UpdateBanner.jsx'

const navClass = ({ isActive }) =>
  `flex h-10 shrink-0 items-center gap-3 whitespace-nowrap rounded-lg px-3 text-sm font-medium lg:w-full ${
    isActive ? 'bg-brand-soft text-brand-dark' : 'text-muted hover:bg-brand-soft hover:text-ink'
  }`

// A small heading above a group of links. Only shown in the side menu (wide screens).
function GroupLabel({ children }) {
  return (
    <p className="mb-1 mt-4 hidden px-3 text-xs font-bold uppercase tracking-wide text-ink lg:block">{children}</p>
  )
}

// The frame around every signed-in page: a menu down the left side and the page on the right.
// On narrow screens the menu becomes a bar across the top, with the links in one swipeable row.
// `menu` says which module this is and what is in its menu (see lib/menus.js).
export default function AppLayout({ menu }) {
  const { logout, isAdmin } = useAuth()
  const { staff, staffId, setStaffId } = useStaffChoice()
  const person = staff.find((s) => String(s.id) === String(staffId))
  // The night login has a single module, so it has no front page to go back to. Admin always has one.
  const hasSeveralModules = isAdmin || modulesFor(false).length > 1

  return (
    <div className="min-h-screen lg:flex">
      <aside className="border-b border-line bg-surface lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-64 lg:shrink-0 lg:flex-col lg:border-b-0 lg:border-r">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-5 lg:py-5">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-lg bg-brand text-white">
              <menu.Icon size={20} aria-hidden="true" />
            </span>
            <div className="leading-tight">
              <span className="block font-semibold">{menu.name}</span>
              <span className="block text-xs text-muted">Achieve HACCP</span>
            </div>
          </div>
        </div>

        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-4 pb-3 lg:flex-1 lg:flex-col lg:gap-0 lg:overflow-y-auto lg:px-3 lg:pb-0">
          {hasSeveralModules && (
            <NavLink to="/" end className={navClass}>
              <LayoutGrid size={18} aria-hidden="true" /> All modules
            </NavLink>
          )}
          {menu.home && (
            <NavLink to={menu.home.to} end className={navClass}>
              <menu.home.Icon size={18} aria-hidden="true" /> {menu.home.label}
            </NavLink>
          )}

          {menu.groups
            .filter((group) => isAdmin || !group.adminOnly)
            .map((group) => (
              <div key={group.label} className="contents">
                <GroupLabel>{group.label}</GroupLabel>
                {group.links.map(({ to, label, Icon, Badge, end }) => (
                  <NavLink key={to} to={to} end={end} className={navClass}>
                    <Icon size={18} aria-hidden="true" /> {label}
                    {Badge && <Badge />}
                  </NavLink>
                ))}
              </div>
            ))}
        </nav>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 lg:flex-col lg:items-stretch lg:p-4">
          <div className="leading-tight">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <UserRound size={16} aria-hidden="true" />
              <span className="sr-only">Who is using this computer</span>
              <select
                value={staffId}
                onChange={(e) => setStaffId(e.target.value)}
                className={`h-9 min-w-0 flex-1 rounded-md border bg-surface px-2 text-sm font-semibold focus:outline-2 focus:outline-brand ${
                  person ? 'border-line' : 'border-near'
                }`}
              >
                <option value="" disabled>
                  Who is using this?
                </option>
                {staff.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <p className="mt-1 text-xs text-muted lg:pl-6">{isAdmin ? 'Admin login (day)' : 'Night login'}</p>
          </div>
          <button
            onClick={logout}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft"
          >
            <LogOut size={16} aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 sm:py-8">
        <UpdateBanner />
        <Outlet />
      </main>
    </div>
  )
}
