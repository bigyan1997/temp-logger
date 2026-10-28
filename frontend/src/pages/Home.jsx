import { useAuth } from '../auth.jsx'

// Placeholder: the real Today checklist (night) and Dashboard (admin) come next.
export default function Home() {
  const { user } = useAuth()

  return (
    <div>
      <h1 className="text-2xl font-semibold">Hello, {user.display_name}</h1>
      <p className="mt-4 rounded-xl border border-line bg-surface p-4 text-muted">
        You are signed in. The reading screens are coming next.
      </p>
    </div>
  )
}
