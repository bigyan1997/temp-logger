// The one Save button at the bottom of a receiving or dispatch screen.
// `count` is how many rows are filled in and not saved yet.
export default function SaveAll({ count, busy, onSave }) {
  return (
    <div className="mt-4 flex items-center gap-4">
      <button
        onClick={onSave}
        disabled={busy || count === 0}
        className="h-12 rounded-lg bg-brand px-8 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {busy ? 'Saving…' : count > 1 ? `Save ${count} readings` : 'Save'}
      </button>
      {count === 0 && <p className="text-sm text-muted">Type a temperature above, then save.</p>}
    </div>
  )
}
