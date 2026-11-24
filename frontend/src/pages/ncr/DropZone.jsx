import { useState } from 'react'

// Wraps a file chooser so files can also be dragged onto it. The server still checks every file.
// `onFiles` gets the dropped files; `disabled` ignores drops (e.g. while saving).
export default function DropZone({ onFiles, disabled = false, className = '', children }) {
  const [over, setOver] = useState(false)

  function dragging(event) {
    if (disabled || !event.dataTransfer.types.includes('Files')) return
    event.preventDefault() // needed, or the browser opens the file instead
    setOver(true)
  }

  function dropped(event) {
    event.preventDefault()
    setOver(false)
    if (!disabled && event.dataTransfer.files.length) onFiles([...event.dataTransfer.files])
  }

  return (
    <div
      onDragEnter={dragging}
      onDragOver={dragging}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOver(false) }}
      onDrop={dropped}
      className={`rounded-xl border-2 border-dashed p-3 ${over ? 'border-brand bg-brand-soft' : 'border-line'} ${className}`}
    >
      {children}
      <p className="mt-2 text-xs text-muted">{over ? 'Drop the files here' : 'You can drag photos and files here.'}</p>
    </div>
  )
}
