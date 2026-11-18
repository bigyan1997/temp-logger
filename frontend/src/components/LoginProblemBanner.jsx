import { KeyRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuth } from '../auth.jsx'
import { LOGIN_PROBLEM_EVENT } from '../lib/loginProblems.js'

// Shown when some information could not be loaded because of the login, so a screen never just looks empty.
// It goes away by itself when that information loads again.
export default function LoginProblemBanner() {
  const { signInAgain } = useAuth()
  const [failing, setFailing] = useState(new Set()) // the data requests that were refused

  useEffect(() => {
    function onChange(event) {
      const { hash, failed } = event.detail
      setFailing((current) => {
        if (current.has(hash) === failed) return current
        const next = new Set(current)
        if (failed) next.add(hash)
        else next.delete(hash)
        return next
      })
    }
    window.addEventListener(LOGIN_PROBLEM_EVENT, onChange)
    return () => window.removeEventListener(LOGIN_PROBLEM_EVENT, onChange)
  }, [])

  if (failing.size === 0) return null
  return (
    <div role="alert" className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-bad/50 bg-red-50 px-4 py-3 text-sm text-bad">
      <KeyRound size={16} aria-hidden="true" />
      <span className="font-medium">Some information could not be loaded because your login has ended or is not allowed to see it. What you see may be incomplete.</span>
      <button onClick={signInAgain} className="h-9 rounded-lg bg-brand px-3 font-medium text-white hover:bg-brand-dark">
        Sign in again
      </button>
    </div>
  )
}
