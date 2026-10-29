// Mirrors the server's rules so staff see the result while typing.
// The server decides in the end; this is only for instant feedback.

export const NEAR_MARGIN = 1 // degrees from the limit that count as "near"

// Accepts "-18", "-18.2", "4", "4.5". Returns a number, or null if it is not a temperature.
export function parseTemp(text) {
  const cleaned = String(text).trim().replace('−', '-') // some keyboards type a long minus
  return /^-?\d{1,2}(\.\d)?$/.test(cleaned) ? Number(cleaned) : null
}

// Colder is always better, so only a reading ABOVE the limit is out of limit.
export function statusFor(value, limit) {
  if (value > limit) return 'out_of_limit'
  if (value > limit - NEAR_MARGIN) return 'near_limit'
  return 'ok'
}

export const formatTemp = (value) => `${Number(value).toFixed(1)} °C`
