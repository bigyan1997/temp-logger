import { QueryCache } from '@tanstack/react-query'
import { ApiError } from '../api/client.js'

// Tells LoginProblemBanner when a screen's data could not be loaded because of the login (401 or 403), and when the
// same data loads again. Most screens show an empty table when a load fails, which looks like "no records".
export const LOGIN_PROBLEM_EVENT = 'login-problem'

const tell = (query, failed) => window.dispatchEvent(new CustomEvent(LOGIN_PROBLEM_EVENT, { detail: { hash: query.queryHash, failed } }))

export const loginProblemCache = () =>
  new QueryCache({
    onError: (error, query) => {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) tell(query, true)
    },
    onSuccess: (_data, query) => tell(query, false),
  })
