import { ChevronRight, LogOut, ShieldCheck } from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { modulesFor } from '../lib/modules.js'

// The front page of Achieve HACCP: one card for each module.
// The night login only has one module, so it goes straight in and never sees this page.
export default function AppHome() {
  const { logout, isAdmin } = useAuth()
  const modules = modulesFor(isAdmin)
  if (!isAdmin && modules.length === 1) return <Navigate to={modules[0].to} replace />

  return (
    <div className="mx-auto min-h-screen max-w-4xl px-4 py-8 sm:px-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-brand text-white">
            <ShieldCheck aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold leading-tight">Achieve HACCP</h1>
            <p className="text-sm text-muted">Achieve Cafe Provisions · {isAdmin ? 'Admin login (day)' : 'Night login'}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="inline-flex h-10 items-center gap-2 rounded-lg border border-line bg-surface px-3 text-sm font-medium hover:bg-brand-soft"
        >
          <LogOut size={16} aria-hidden="true" /> Sign out
        </button>
      </header>

      <h2 className="mb-3 mt-10 text-sm font-medium uppercase tracking-wide text-muted">Choose what to open</h2>
      <ul className="grid gap-4 sm:grid-cols-2">
        {modules.map(({ key, name, description, tables, to, Icon }) => (
          <li key={key}>
            <Link
              to={to}
              className="flex h-full flex-col rounded-2xl border border-line bg-surface p-5 shadow-sm hover:border-brand hover:bg-brand-soft"
            >
              <span className="grid size-11 place-items-center rounded-xl bg-brand text-white">
                <Icon aria-hidden="true" />
              </span>
              <span className="mt-4 text-lg font-semibold">{name}</span>
              <span className="mt-1 text-sm text-muted">{description}</span>
              <span className="mt-1 text-xs text-muted">{tables}</span>
              <span className="mt-4 flex items-center font-medium text-brand-dark">
                Open <ChevronRight size={16} aria-hidden="true" />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
