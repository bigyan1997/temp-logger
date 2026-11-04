import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, ApiError, ensureCsrf } from './api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

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
          await new Promise((resolve) => setTimeout(resolve, 3000))
        }
      }
      return null
    }
    checkSignedIn().then(setUser).finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    await ensureCsrf()
    const u = await api('/auth/login/', { method: 'POST', body: { email, password } })
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    await api('/auth/logout/', { method: 'POST' })
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAdmin: user?.role === 'admin' }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
