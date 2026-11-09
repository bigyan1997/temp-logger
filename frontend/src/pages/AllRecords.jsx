import { useSearchParams } from 'react-router-dom'
import CalibrationRecords from './calibration/CalibrationRecords.jsx'
import Records from './admin/Records.jsx'

// One tab for each kind of record. `kind` is what Records.jsx understands; Calibration has its own page.
const tabs = [
  { key: 'storage', label: 'Coolrooms & freezers' },
  { key: 'receiving', label: 'Receiving' },
  { key: 'dispatch', label: 'Dispatch' },
  { key: 'calibration', label: 'Calibration' },
]

// Every saved record of every module in one place (day staff only). The tab is kept in the address (?tab=).
export default function AllRecords() {
  const [params, setParams] = useSearchParams()
  const tab = tabs.some((t) => t.key === params.get('tab')) ? params.get('tab') : 'storage'

  return (
    <div>
      <h1 className="text-2xl font-semibold">Records</h1>
      <div role="tablist" aria-label="Kind of record" className="mt-4 flex flex-wrap gap-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setParams({ tab: t.key })}
            className={`h-10 rounded-lg px-4 font-medium ${tab === t.key ? 'bg-brand text-white' : 'border border-line bg-surface hover:bg-brand-soft'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* key: start each tab with fresh filters */}
      {tab === 'calibration' ? <CalibrationRecords key={tab} embedded /> : <Records key={tab} kind={tab} />}
    </div>
  )
}
