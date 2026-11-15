import { FileText } from 'lucide-react'

// What the file choosers offer. The server checks each file's contents and is what really decides.
export const FILE_ACCEPT = '.jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.rtf,.txt,.csv'
export const FILE_HELP = 'Photos (JPG, PNG, GIF, WEBP) or documents (PDF, Word, Excel, PowerPoint, TXT, CSV), up to 20 MB each.'

// A picture is drawn small; any other file (PDF, Word...) is a tile with its type, so it is clear it is not a photo.
// `size` is the Tailwind width and height of the tile, e.g. "h-32 w-44".
export default function Attachment({ photo, size }) {
  const link = 'block rounded-lg border border-line'
  if (photo.is_picture) {
    return (
      <a href={photo.url} target="_blank" rel="noreferrer">
        <img src={photo.url} alt={photo.original_name} loading="lazy" className={`${size} ${link} object-cover`} />
      </a>
    )
  }
  const ending = photo.original_name.includes('.') ? photo.original_name.split('.').pop().toUpperCase() : 'FILE'
  return (
    <a href={photo.url} target="_blank" rel="noreferrer" aria-label={`Open ${photo.original_name}`} className={`${size} ${link} flex flex-col items-center justify-center gap-1 bg-brand-soft text-brand-dark hover:bg-surface`}>
      <FileText size={28} aria-hidden="true" />
      <span className="text-sm font-semibold">{ending}</span>
    </a>
  )
}
