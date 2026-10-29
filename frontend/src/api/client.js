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
  return problems.length ? problems.join(' ') : `Something went wrong (${status}).`
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
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') headers['X-CSRFToken'] = getCookie('csrftoken')

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    ...(body !== undefined && { body: JSON.stringify(body) }),
  })

  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, data)
  return data
}

export const ensureCsrf = () => api('/auth/csrf/')
