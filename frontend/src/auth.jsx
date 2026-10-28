import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, ApiError, ensureCsrf } from './api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ensureCsrf()
      .then(() => api('/auth/me/'))
      .then(setUser)
      .catch((err) => {
        if (!(err instanceof ApiError)) console.error(err)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username, password) => {
    await ensureCsrf()
    const u = await api('/auth/login/', { method: 'POST', body: { username, password } })
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
