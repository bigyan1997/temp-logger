// Move the cursor to the next box on the screen that matches `selector`, after `from`.
// Returns false when there is no next one, so the caller can do something else (like save).
export function focusNext(from, selector) {
  const boxes = [...document.querySelectorAll(selector)]
  const next = boxes[boxes.indexOf(from) + 1]
  if (!next) return false
  next.focus()
  if (next.type === 'text') next.select() // so typing replaces what is there
  return true
}

// The next temperature box, skipping rows that are saved or marked "No delivery".
export const focusNextTemperature = (from) => focusNext(from, 'input[data-temperature]:not(:disabled)')

// For a form with several fields: Enter moves to the next field instead of saving the form. After the last
// field it lands on the Save button, so a second Enter saves. Use it as the form's onKeyDown.
export function enterMovesOn(event) {
  if (event.key !== 'Enter' || event.target.tagName !== 'INPUT') return
  event.preventDefault()
  const fields = [...event.currentTarget.querySelectorAll('input:not(:disabled), select:not(:disabled), button[type="submit"]')]
  const next = fields[fields.indexOf(event.target) + 1]
  if (!next) return
  next.focus()
  if (next.type === 'text') next.select()
}
