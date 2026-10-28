import { LogOut } from 'lucide-react'
import { useAuth } from '../auth.jsx'

// Placeholder: the real Today checklist (night) and Dashboard (admin) come in the next steps.
export default function Home() {
  const { user, logout, isAdmin } = useAuth()
  return (
    <main className="mx-auto max-w-xl px-4 py-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-muted">{isAdmin ? 'Admin (day)' : 'Night shift'}</p>
          <h1 className="text-2xl font-semibold">Hello, {user.display_name}</h1>
        </div>
        <button
          onClick={logout}
          className="inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-surface px-4 text-sm font-medium hover:bg-brand-soft"
        >
          <LogOut size={16} aria-hidden="true" /> Sign out
        </button>
      </div>
      <p className="mt-6 rounded-xl border border-line bg-surface p-4 text-muted">
        You are signed in. The reading screens are coming next.
      </p>
    </main>
  )
}
