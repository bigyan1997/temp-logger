import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import AppLayout from './components/AppLayout.jsx'
import { cleaningMenu, ncrMenu, recordsMenu, settingsMenu, temperatureMenu } from './lib/menus.js'
import CalibrationHome from './pages/calibration/CalibrationHome.jsx'
import CalibrationRecords from './pages/calibration/CalibrationRecords.jsx'
import NewCalibration from './pages/calibration/NewCalibration.jsx'
import NcrDetail from './pages/ncr/NcrDetail.jsx'
import NcrHome from './pages/ncr/NcrHome.jsx'
import NewNcr from './pages/ncr/NewNcr.jsx'
import CleaningHome from './pages/cleaning/CleaningHome.jsx'
import CleaningNotifications from './pages/cleaning/CleaningNotifications.jsx'
import CleaningRecords from './pages/cleaning/CleaningRecords.jsx'
import CleaningTasks from './pages/cleaning/CleaningTasks.jsx'
import AllRecords from './pages/AllRecords.jsx'
import AppHome from './pages/AppHome.jsx'
import AuditLog from './pages/admin/AuditLog.jsx'
import Records from './pages/admin/Records.jsx'
import Reports from './pages/admin/Reports.jsx'
import Settings, { Lists } from './pages/admin/Settings.jsx'
import Trends from './pages/admin/Trends.jsx'
import Home from './pages/Home.jsx'
import LogDispatch from './pages/LogDispatch.jsx'
import LogReceiving from './pages/LogReceiving.jsx'
import LogStorage from './pages/LogStorage.jsx'
import Login from './pages/Login.jsx'

// Shown while the app checks that you are signed in. If the server is slow to answer, say so and offer the login page.
function StartingUp({ trouble }) {
  return (
    <div className="grid min-h-screen place-items-center px-4 text-center">
      {trouble ? (
        <div role="status">
          <p className="font-medium">Cannot reach the server yet. Still trying…</p>
          <p className="mt-1 text-sm text-muted">If this carries on, check the computer is on and connected, or sign in again.</p>
          <Link to="/login" className="mt-4 inline-block rounded-lg bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-dark">
            Sign in again
          </Link>
        </div>
      ) : (
        <p className="text-muted">Loading…</p>
      )}
    </div>
  )
}

// Everything except the login page needs a signed-in user.
function RequireAuth({ children }) {
  const { user, loading, trouble } = useAuth()
  if (loading) return <StartingUp trouble={trouble} />
  if (!user) return <Navigate to="/login" replace />
  return children
}

// Pages only the day (admin) login may open.
function AdminOnly({ children }) {
  const { isAdmin } = useAuth()
  return isAdmin ? children : <Navigate to="/temperature" replace />
}

const adminPage = (page) => <AdminOnly>{page}</AdminOnly>

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppHome />
          </RequireAuth>
        }
      />
      {/* The Temperature Logger module. Its pages keep their own short paths. */}
      <Route
        element={
          <RequireAuth>
            <AppLayout menu={temperatureMenu} />
          </RequireAuth>
        }
      >
        <Route path="/temperature" element={<Home />} />
        <Route path="/log/storage" element={<LogStorage />} />
        <Route path="/log/receiving" element={<LogReceiving />} />
        <Route path="/log/dispatch" element={<LogDispatch />} />

        <Route path="/records" element={adminPage(<Records />)} />
        <Route path="/trends" element={adminPage(<Trends />)} />
        <Route path="/reports" element={adminPage(<Reports />)} />
        <Route path="/audit" element={adminPage(<AuditLog />)} />
        <Route path="/lists/:section?" element={adminPage(<Lists />)} />
      </Route>

      {/* The Cleaning & Maintenance module: Table 8 cleaning and Table 14 calibration. Day staff only. */}
      <Route
        element={
          <RequireAuth>
            <AppLayout menu={cleaningMenu} />
          </RequireAuth>
        }
      >
        <Route path="/cleaning" element={adminPage(<CleaningHome />)} />
        <Route path="/cleaning/records" element={adminPage(<CleaningRecords />)} />
        <Route path="/cleaning/tasks" element={adminPage(<CleaningTasks />)} />
        <Route path="/cleaning/notifications" element={adminPage(<CleaningNotifications />)} />
        <Route path="/cleaning/audit" element={adminPage(<AuditLog module="cleaning" />)} />
        <Route path="/calibration" element={adminPage(<CalibrationHome />)} />
        <Route path="/calibration/new" element={adminPage(<NewCalibration />)} />
        <Route path="/calibration/records" element={adminPage(<CalibrationRecords />)} />
        <Route path="/calibration/audit" element={adminPage(<AuditLog module="calibration" />)} />
      </Route>

      {/* The Non-Conformance Reports module (Table 5): day staff only. */}
      <Route
        element={
          <RequireAuth>
            <AppLayout menu={ncrMenu} />
          </RequireAuth>
        }
      >
        <Route path="/ncr" element={adminPage(<NcrHome />)} />
        <Route path="/ncr/new" element={adminPage(<NewNcr />)} />
        <Route path="/ncr/audit" element={adminPage(<AuditLog module="nonconformance" />)} />
        <Route path="/ncr/:id" element={adminPage(<NcrDetail />)} />
      </Route>

      {/* Settings shared by the whole app. Day staff only. */}
      <Route
        element={
          <RequireAuth>
            <AppLayout menu={settingsMenu} />
          </RequireAuth>
        }
      >
        <Route path="/settings/:section?" element={adminPage(<Settings />)} />
      </Route>

      {/* All records of every module, in tabs. Day staff only. */}
      <Route
        element={
          <RequireAuth>
            <AppLayout menu={recordsMenu} />
          </RequireAuth>
        }
      >
        <Route path="/all-records" element={adminPage(<AllRecords />)} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
