// A line chart of one unit's temperatures with its limit as a dashed line.
// Points use different shapes as well as colours: circle = in range, triangle = near the limit,
// diamond = out of limit. Positions come from one pair of scales so labels match the data.

const WIDTH = 900
const HEIGHT = 320
const MARGIN = { top: 16, right: 24, bottom: 36, left: 52 }

const shortDate = new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short', timeZone: 'Australia/Sydney' })

function Marker({ x, y, status }) {
  if (status === 'out_of_limit') {
    return <path d={`M${x} ${y - 7} L${x + 7} ${y} L${x} ${y + 7} L${x - 7} ${y} Z`} className="fill-bad" />
  }
  if (status === 'near_limit') {
    return <path d={`M${x} ${y - 7} L${x + 7} ${y + 6} L${x - 7} ${y + 6} Z`} className="fill-near" />
  }
  return <circle cx={x} cy={y} r={4.5} className="fill-brand" />
}

export default function TrendChart({ points, limit }) {
  if (points.length === 0) {
    return <p className="rounded-xl border border-line bg-surface p-6 text-muted">No readings in this period.</p>
  }

  const times = points.map((p) => new Date(p.slot).getTime())
  const values = points.map((p) => Number(p.value))
  const firstTime = Math.min(...times)
  const lastTime = Math.max(...times)

  const lowest = Math.floor(Math.min(...values, limit) - 2)
  const highest = Math.ceil(Math.max(...values, limit) + 2)

  const plotWidth = WIDTH - MARGIN.left - MARGIN.right
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  const x = (time) => MARGIN.left + (lastTime === firstTime ? plotWidth / 2 : ((time - firstTime) / (lastTime - firstTime)) * plotWidth)
  const y = (value) => MARGIN.top + ((highest - value) / (highest - lowest)) * plotHeight

  const yTicks = Array.from({ length: 5 }, (_, i) => Math.round(lowest + ((highest - lowest) * i) / 4))
  const xTicks = [...new Set(times.map((t) => shortDate.format(t)))]
    .slice(0, 7)
    .map((label) => ({ label, time: times[points.findIndex((p) => shortDate.format(new Date(p.slot)) === label)] }))

  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(times[i])} ${y(values[i])}`).join(' ')

  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface p-3">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto min-w-[640px] w-full" role="img" aria-label="Temperature trend">
        {yTicks.map((tick) => (
          <g key={tick}>
            <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(tick)} y2={y(tick)} className="stroke-line" strokeWidth="1" />
            <text x={MARGIN.left - 8} y={y(tick) + 4} textAnchor="end" className="fill-muted text-[12px]">{tick}°</text>
          </g>
        ))}
        {xTicks.map(({ label, time }) => (
          <text key={label} x={x(time)} y={HEIGHT - 12} textAnchor="middle" className="fill-muted text-[12px]">{label}</text>
        ))}

        <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(limit)} y2={y(limit)} className="stroke-bad" strokeWidth="1.5" strokeDasharray="6 4" />
        <text x={WIDTH - MARGIN.right} y={y(limit) - 6} textAnchor="end" className="fill-bad text-[12px] font-medium">Limit {limit} °C</text>

        <path d={line} fill="none" className="stroke-brand" strokeWidth="1.5" />
        {points.map((p, i) => (
          <Marker key={p.slot} x={x(times[i])} y={y(values[i])} status={p.status} />
        ))}
      </svg>

      <ul className="mt-2 flex flex-wrap gap-4 text-sm text-muted">
        <li>● In range</li>
        <li>▲ Near limit</li>
        <li>◆ Out of limit</li>
      </ul>
    </div>
  )
}
