// Small fetch wrapper: JSON in/out, session cookie, CSRF token on writes.

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : ''
}

// Every text message inside an error body, however deeply it is nested.
function messagesIn(value) {
  if (typeof value === 'string') return [value]
  if (Array.isArray(value)) return value.flatMap(messagesIn)
  if (value && typeof value === 'object') return Object.values(value).flatMap(messagesIn)
  return []
}

// Turns an API error body into one readable sentence.
// Handles {message: "..."} and Django-style {field: ["problem"]}, including nested fields.
function describeError(body, status) {
  if (typeof body?.message === 'string') return body.message
  const problems = messagesIn(body)
  const text = problems.join(' ')
  // Login problems get plain words, not the server's technical ones ("CSRF Failed...", "credentials were not provided").
  if (status === 401 || /credentials were not provided/i.test(text)) return 'Your login has ended. Please sign in again.'
  if (status === 403 && /permission/i.test(text)) return 'This login is not allowed to do that. Sign in with the day login.'
  if (status === 403 && (!text || /csrf/i.test(text))) return 'This page is out of date. Refresh it (F5) or sign in again, then try again.'
  return text || `Something went wrong (${status}).`
}

export class ApiError extends Error {
  constructor(status, body) {
    super(describeError(body, status))
    this.status = status
    this.code = body?.code
    this.body = body
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  const isUpload = body instanceof FormData // files: the browser sets the content type itself
  if (body !== undefined && !isUpload) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') headers['X-CSRFToken'] = getCookie('csrftoken')

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    ...(body !== undefined && { body: isUpload ? body : JSON.stringify(body) }),
  })

  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if ((response.status === 401 || response.status === 403) && !path.startsWith('/auth/')) {
    window.dispatchEvent(new Event('session-check')) // maybe the session ended; auth.jsx checks and signs out if so
  }
  if (!response.ok) throw new ApiError(response.status, data)
  return data
}

export const ensureCsrf = () => api('/auth/csrf/')
