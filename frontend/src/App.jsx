import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="grid min-h-screen place-items-center text-muted">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Home />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
