// Small fetch wrapper: JSON in/out, session cookie, CSRF token on writes.

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : ''
}

// Turns an API error body into one readable sentence.
// Handles {message: "..."} and Django-style {field: ["problem", ...]}.
function describeError(body, status) {
  if (body?.message) return body.message
  if (body && typeof body === 'object') {
    const problems = Object.values(body).flat().filter((v) => typeof v === 'string')
    if (problems.length) return problems.join(' ')
  }
  return `Something went wrong (${status}).`
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
