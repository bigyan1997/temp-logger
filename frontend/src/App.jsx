import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import AppLayout from './components/AppLayout.jsx'
import AuditLog from './pages/admin/AuditLog.jsx'
import Records from './pages/admin/Records.jsx'
import Reports from './pages/admin/Reports.jsx'
import Settings from './pages/admin/Settings.jsx'
import Trends from './pages/admin/Trends.jsx'
import Home from './pages/Home.jsx'
import LogDispatch from './pages/LogDispatch.jsx'
import LogReceiving from './pages/LogReceiving.jsx'
import LogStorage from './pages/LogStorage.jsx'
import Login from './pages/Login.jsx'

// Everything except the login page needs a signed-in user.
function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="grid min-h-screen place-items-center text-muted">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

// Pages only the day (admin) login may open.
function AdminOnly({ children }) {
  const { isAdmin } = useAuth()
  return isAdmin ? children : <Navigate to="/" replace />
}

const adminPage = (page) => <AdminOnly>{page}</AdminOnly>

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/log/storage" element={<LogStorage />} />
        <Route path="/log/receiving" element={<LogReceiving />} />
        <Route path="/log/dispatch" element={<LogDispatch />} />

        <Route path="/records" element={adminPage(<Records />)} />
        <Route path="/trends" element={adminPage(<Trends />)} />
        <Route path="/reports" element={adminPage(<Reports />)} />
        <Route path="/audit" element={adminPage(<AuditLog />)} />
        <Route path="/settings/:section?" element={adminPage(<Settings />)} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
