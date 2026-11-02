import {
  BarChart3,
  ClipboardList,
  FileText,
  History,
  Home,
  LogOut,
  PackageCheck,
  Settings,
  Snowflake,
  Thermometer,
  Truck,
  UserRound,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { useStaffChoice } from './StaffPicker.jsx'

const navClass = ({ isActive }) =>
  `flex h-10 shrink-0 items-center gap-3 whitespace-nowrap rounded-lg px-3 text-sm font-medium lg:w-full ${
    isActive ? 'bg-brand-soft text-brand-dark' : 'text-muted hover:bg-brand-soft hover:text-ink'
  }`

// What everyone uses to log readings.
const loggingLinks = [
  { to: '/log/storage', label: 'Storage', Icon: Snowflake },
  { to: '/log/receiving', label: 'Receiving', Icon: PackageCheck },
  { to: '/log/dispatch', label: 'Dispatch', Icon: Truck },
]

// Admin only: look at records, trends and reports, and manage settings.
const adminLinks = [
  { to: '/records', label: 'Records', Icon: ClipboardList },
  { to: '/trends', label: 'Trends', Icon: BarChart3 },
  { to: '/reports', label: 'Reports', Icon: FileText },
  { to: '/audit', label: 'Audit log', Icon: History },
  { to: '/settings', label: 'Settings', Icon: Settings },
]

// A small heading above a group of links. Only shown in the side menu (wide screens).
function GroupLabel({ children }) {
  return (
    <p className="mb-1 mt-4 hidden px-3 text-xs font-medium uppercase tracking-wide text-muted lg:block">{children}</p>
  )
}

// The frame around every signed-in page: a menu down the left side and the page on the right.
// On narrow screens the menu becomes a bar across the top, with the links in one swipeable row.
export default function AppLayout() {
  const { logout, isAdmin } = useAuth()
  const { staff, staffId, setStaffId } = useStaffChoice()
  const person = staff.find((s) => String(s.id) === String(staffId))

  return (
    <div className="min-h-screen lg:flex">
      <aside className="border-b border-line bg-surface lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-64 lg:shrink-0 lg:flex-col lg:border-b-0 lg:border-r">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-5 lg:py-5">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-lg bg-brand text-white">
              <Thermometer size={20} aria-hidden="true" />
            </span>
            <span className="font-semibold">Temperature Logger</span>
          </div>
        </div>

        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-4 pb-3 lg:flex-1 lg:flex-col lg:gap-0 lg:overflow-y-auto lg:px-3 lg:pb-0">
          <NavLink to="/" end className={navClass}>
            <Home size={18} aria-hidden="true" /> Home
          </NavLink>

          <GroupLabel>Log</GroupLabel>
          {loggingLinks.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={navClass}>
              <Icon size={18} aria-hidden="true" /> {label}
            </NavLink>
          ))}

          {isAdmin && (
            <>
              <GroupLabel>Admin</GroupLabel>
              {adminLinks.map(({ to, label, Icon }) => (
                <NavLink key={to} to={to} className={navClass}>
                  <Icon size={18} aria-hidden="true" /> {label}
                </NavLink>
              ))}
            </>
          )}
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
        <Outlet />
      </main>
    </div>
  )
}
