import { useAuth } from '../auth.jsx'
import Dashboard from './admin/Dashboard.jsx'
import Today from './Today.jsx'

// Day (admin) staff land on the dashboard; night staff land on today's checklist.
export default function Home() {
  const { isAdmin } = useAuth()
  return isAdmin ? <Dashboard /> : <Today />
}
