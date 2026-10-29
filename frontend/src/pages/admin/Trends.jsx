import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/client.js'
import TrendChart from '../../components/TrendChart.jsx'
import { useActiveList } from '../../lib/useActiveList.js'

const periods = [
  { days: 7, label: 'Last 7 days' },
  { days: 14, label: 'Last 14 days' },
  { days: 30, label: 'Last 30 days' },
]

const selectClass = 'h-11 rounded-lg border border-line bg-surface px-3 focus:border-brand focus:outline-2 focus:outline-brand'

export default function Trends() {
  const { data: units = [] } = useActiveList('/units/')
  const [unitId, setUnitId] = useState('')
  const [days, setDays] = useState(14)
  const chosen = unitId || units[0]?.id

  const { data } = useQuery({
    queryKey: ['trends', chosen, days],
    queryFn: () => {
      const to = new Date()
      const from = new Date(to.getTime() - (days - 1) * 86_400_000)
      return api(`/trends/?unit=${chosen}&from=${from.toISOString().slice(0, 10)}&to=${to.toISOString().slice(0, 10)}`)
    },
    enabled: Boolean(chosen),
  })

  return (
    <div className="max-w-5xl">
      <h1 className="text-2xl font-semibold">Trends</h1>
      <p className="mt-1 text-muted">How each coolroom and freezer has been running. The dashed line is the limit.</p>

      <div className="mt-4 flex flex-wrap gap-3">
        <select aria-label="Unit" value={chosen ?? ''} onChange={(e) => setUnitId(e.target.value)} className={selectClass}>
          {units.map((u) => (
            <option key={u.id} value={u.id}>{u.name}</option>
          ))}
        </select>
        <select aria-label="Period" value={days} onChange={(e) => setDays(Number(e.target.value))} className={selectClass}>
          {periods.map((p) => (
            <option key={p.days} value={p.days}>{p.label}</option>
          ))}
        </select>
      </div>

      <div className="mt-6">
        {data ? <TrendChart points={data.points} limit={Number(data.unit.limit)} /> : <p className="text-muted">Loading…</p>}
      </div>
    </div>
  )
}
