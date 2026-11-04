import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api, ApiError, ensureCsrf } from './api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [trouble, setTrouble] = useState(false) // the server did not answer the first time; still retrying
  const [notice, setNotice] = useState('') // shown on the login page, e.g. "Your session ended"
  const checking = useRef(false)

  useEffect(() => {
    // Only a 401/403 means "not signed in". A network blip or a 5xx (the server restarting
    // during a deploy) must not look like a sign-out, so those are retried for a while.
    async function checkSignedIn() {
      for (let attempt = 0; attempt < 10; attempt++) {
        try {
          await ensureCsrf()
          return await api('/auth/me/')
        } catch (err) {
          if (err instanceof ApiError && (err.status === 401 || err.status === 403)) return null
          setTrouble(true)
          await new Promise((resolve) => setTimeout(resolve, 3000))
        }
      }
      return null
    }
    checkSignedIn().then(setUser).finally(() => setLoading(false))
  }, [])

  // Any screen's data call that gets 401/403 may mean the session ended (the server restarted, or it
  // expired). Ask the server; only a 401/403 from /auth/me/ signs out, since 403 can also mean "not allowed".
  useEffect(() => {
    async function recheck() {
      if (checking.current) return
      checking.current = true
      try {
        await api('/auth/me/')
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setNotice('Your session ended. Please sign in again.')
          setUser(null)
        }
      } finally {
        checking.current = false
      }
    }
    window.addEventListener('session-check', recheck)
    return () => window.removeEventListener('session-check', recheck)
  }, [])

  const login = useCallback(async (email, password) => {
    await ensureCsrf()
    const u = await api('/auth/login/', { method: 'POST', body: { email, password } })
    setNotice('')
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    await api('/auth/logout/', { method: 'POST' })
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, trouble, notice, login, logout, isAdmin: user?.role === 'admin' }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
