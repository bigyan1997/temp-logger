import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client.js'

// Offers a reload once a newer build of the app has been deployed. It never reloads by itself,
// because that could throw away readings someone is halfway through typing.
export default function UpdateBanner() {
  const { data } = useQuery({
    queryKey: ['app-version'],
    queryFn: () => api('/version/'),
    refetchInterval: 5 * 60 * 1000,
  })
  const [loaded, setLoaded] = useState(null) // the version this page was opened with
  const current = data?.version
  if (current && loaded === null) setLoaded(current)

  if (!current || current === loaded) return null
  return (
    <div role="status" className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-brand bg-brand-soft px-4 py-3 text-sm">
      <RefreshCw size={16} aria-hidden="true" />A new version of the Temperature Logger is ready.
      <button onClick={() => window.location.reload()} className="h-9 rounded-lg bg-brand px-3 font-medium text-white hover:bg-brand-dark">
        Refresh now
      </button>
    </div>
  )
}
