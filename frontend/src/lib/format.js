const TIME_ZONE = 'Australia/Sydney'

const dateTime = new Intl.DateTimeFormat('en-AU', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
  timeZone: TIME_ZONE,
})

const longDate = new Intl.DateTimeFormat('en-AU', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: TIME_ZONE,
})

// "Mon 2 Nov, 9:00 am" in Sydney time, whatever the computer's own time zone is.
export const formatDateTime = (iso) => dateTime.format(new Date(iso))

// "Monday 2 November 2026"
export const formatLongDate = (date = new Date()) => longDate.format(date)

// Today's date in Sydney as "2026-11-02", the format the API uses.
export const todayInSydney = () => new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE }).format(new Date())

// "9:00 am" in Sydney time.
const timeOnly = new Intl.DateTimeFormat('en-AU', { hour: 'numeric', minute: '2-digit', timeZone: TIME_ZONE })
export const formatTime = (iso) => timeOnly.format(new Date(iso))
