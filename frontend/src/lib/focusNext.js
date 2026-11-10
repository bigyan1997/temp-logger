// Move the cursor to the next temperature box on the screen (skipping rows that are saved or marked "No delivery").
// Returns false when there is no next box, so the caller can save instead.
export function focusNextTemperature(from) {
  const boxes = [...document.querySelectorAll('input[data-temperature]:not(:disabled)')]
  const next = boxes[boxes.indexOf(from) + 1]
  if (!next) return false
  next.focus()
  next.select()
  return true
}
