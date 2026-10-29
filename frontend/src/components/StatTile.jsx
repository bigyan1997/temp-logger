import { AlertTriangle, CheckCircle2 } from 'lucide-react'

// Colour is never the only signal: every attention tile also has an icon and words.
const tones = {
  neutral: 'border-line',
  good: 'border-ok/40',
  warn: 'border-near/50',
  bad: 'border-bad/50',
}

const numberTones = { neutral: 'text-ink', good: 'text-ok', warn: 'text-near', bad: 'text-bad' }

// One big number with a label, for the top row of the dashboard.
// `attention`: true when the number is something staff must act on.
export default function StatTile({ label, value, attention = false, tone = 'bad', note }) {
  const shown = attention && value > 0 ? tone : attention ? 'good' : 'neutral'
  const Icon = attention ? (value > 0 ? AlertTriangle : CheckCircle2) : null

  return (
    <div className={`rounded-xl border bg-surface p-4 ${tones[shown]}`}>
      <p className="text-sm font-medium text-muted">{label}</p>
      <p className={`mt-1 text-4xl font-semibold tabular-nums ${numberTones[shown]}`}>{value}</p>
      {Icon && (
        <p className={`mt-1 flex items-center gap-1 text-sm ${numberTones[shown]}`}>
          <Icon size={14} aria-hidden="true" />
          {value > 0 ? note : 'All clear'}
        </p>
      )}
    </div>
  )
}
