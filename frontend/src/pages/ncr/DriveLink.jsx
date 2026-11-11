import { useQuery } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { api } from '../../api/client.js'

// "Open in Google Drive": shown only when the server knows the Drive folder (GOOGLE_DRIVE_FOLDER_ID or GOOGLE_DRIVE_URL).
export default function DriveLink() {
  const { data } = useQuery({ queryKey: ['ncr-summary'], queryFn: () => api('/non-conformances/summary/') })
  if (!data?.drive_url) return null
  return (
    <a href={data.drive_url} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center gap-2 rounded-lg border border-line px-3 text-sm font-medium hover:bg-brand-soft">
      <ExternalLink size={16} aria-hidden="true" /> Open in Google Drive
    </a>
  )
}
