import { CheckCircle2 } from 'lucide-react'

// A titled box on the dashboard, with a count badge when there is something to look at.
export function Panel({ title, count, children }) {
  return (
    <section className="rounded-xl border border-line bg-surface">
      <h2 className="flex items-center justify-between border-b border-line px-4 py-3 font-semibold">
        {title}
        {count > 0 && <span className="rounded-full bg-brand-soft px-2 text-sm text-brand-dark">{count}</span>}
      </h2>
      {children}
    </section>
  )
}

export function AllClear({ children }) {
  return (
    <p className="flex items-center gap-2 px-4 py-4 text-ok">
      <CheckCircle2 size={18} aria-hidden="true" /> {children}
    </p>
  )
}
