import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/client.js'
import { formatDateTime } from '../../lib/format.js'

const PAGE_SIZE = 50

// A permanent list of corrections and important changes. Nobody can edit or delete it.
export default function AuditLog() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['audit-log', page],
    queryFn: () => api(`/audit-log/?page=${page}`),
  })
  const entries = data?.results ?? []
  const pages = Math.max(1, Math.ceil((data?.count ?? 0) / PAGE_SIZE))

  return (
    <div className="max-w-5xl">
      <h1 className="text-2xl font-semibold">Audit log</h1>
      <p className="mt-1 text-muted">Voided entries, corrections, temperature limit changes and login changes. This list can never be edited.</p>

      <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[640px] text-left">
          <thead className="border-b border-line text-sm text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">When</th>
              <th className="px-4 py-3 font-medium">Who</th>
              <th className="px-4 py-3 font-medium">What happened</th>
              <th className="px-4 py-3 font-medium">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading && <tr><td colSpan={4} className="px-4 py-3 text-muted">Loading…</td></tr>}
            {!isLoading && entries.length === 0 && <tr><td colSpan={4} className="px-4 py-3 text-muted">Nothing has been changed yet.</td></tr>}
            {entries.map((e) => (
              <tr key={e.id}>
                <td className="whitespace-nowrap px-4 py-3 text-sm">{formatDateTime(e.at)}</td>
                <td className="px-4 py-3">{e.user_name}</td>
                <td className="px-4 py-3">{e.summary}</td>
                <td className="px-4 py-3 text-muted">{e.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="mt-3 flex items-center gap-3">
          <button disabled={page === 1} onClick={() => setPage(page - 1)} className="h-10 rounded-lg border border-line px-4 disabled:opacity-40">
            Newer
          </button>
          <span className="text-sm text-muted">Page {page} of {pages}</span>
          <button disabled={page >= pages} onClick={() => setPage(page + 1)} className="h-10 rounded-lg border border-line px-4 disabled:opacity-40">
            Older
          </button>
        </div>
      )}
    </div>
  )
}
