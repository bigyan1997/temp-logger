// A line chart of one unit's temperatures with its limit as a dashed line.
// Points use different shapes as well as colours: circle = in range, triangle = near the limit,
// diamond = out of limit. Positions come from one pair of scales so labels match the data.
// Hovering (or tabbing to) a point shows its temperature and time.

import { useState } from 'react'

const WIDTH = 900
const HEIGHT = 320
const MARGIN = { top: 16, right: 24, bottom: 36, left: 52 }

const MIN_LABEL_GAP = 60
const TOOLTIP_WIDTH = 170
const STATUS_WORDS = { near_limit: 'Near limit', out_of_limit: 'Out of limit' }

const shortDate = new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short', timeZone: 'Australia/Sydney' })
const dateTime = new Intl.DateTimeFormat('en-AU', {
  weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', timeZone: 'Australia/Sydney',
})

function Marker({ x, y, status }) {
  if (status === 'out_of_limit') {
    return <path d={`M${x} ${y - 7} L${x + 7} ${y} L${x} ${y + 7} L${x - 7} ${y} Z`} className="fill-bad" />
  }
  if (status === 'near_limit') {
    return <path d={`M${x} ${y - 7} L${x + 7} ${y + 6} L${x - 7} ${y + 6} Z`} className="fill-near" />
  }
  return <circle cx={x} cy={y} r={4.5} className="fill-brand" />
}

// One label per day, at that day's first reading, skipping any that would crowd the one before.
function dateTicks(times, x) {
  const ticks = []
  for (const time of times) {
    const label = shortDate.format(time)
    const previous = ticks[ticks.length - 1]
    if (previous && (previous.label === label || x(time) - x(previous.time) < MIN_LABEL_GAP)) continue
    ticks.push({ label, time })
  }
  return ticks
}

// The box shown above a point when it is hovered or focused: the temperature, when, and the status in words.
function Tooltip({ x, y, point }) {
  const statusText = STATUS_WORDS[point.status]
  const height = statusText ? 62 : 44
  const left = Math.min(Math.max(x - TOOLTIP_WIDTH / 2, MARGIN.left), WIDTH - MARGIN.right - TOOLTIP_WIDTH)
  // Show it below the point when there is no room above.
  const top = y - height - 12 < 0 ? y + 12 : y - height - 12

  return (
    <g pointerEvents="none">
      <rect x={left} y={top} width={TOOLTIP_WIDTH} height={height} rx="6" className="fill-surface stroke-line" strokeWidth="1" />
      <text x={left + 10} y={top + 20} className="fill-ink text-[14px] font-semibold">{Number(point.value).toFixed(1)} °C</text>
      <text x={left + 10} y={top + 37} className="fill-muted text-[12px]">{dateTime.format(new Date(point.slot))}</text>
      {statusText && <text x={left + 10} y={top + 54} className="fill-muted text-[12px]">{statusText}</text>}
    </g>
  )
}

export default function TrendChart({ points, limit }) {
  const [hoveredIndex, setHoveredIndex] = useState(null)

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
  const xTicks = dateTicks(times, x)

  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(times[i])} ${y(values[i])}`).join(' ')
  const hovered = hoveredIndex === null ? null : points[hoveredIndex]

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

        {/* Bigger invisible circles so a point is easy to hover; Tab also moves between them. */}
        {points.map((p, i) => (
          <circle
            key={`hit-${p.slot}`}
            cx={x(times[i])}
            cy={y(values[i])}
            r="12"
            fill="transparent"
            className="cursor-pointer outline-none"
            tabIndex={0}
            aria-label={`${Number(p.value).toFixed(1)} °C, ${dateTime.format(new Date(p.slot))}`}
            onMouseEnter={() => setHoveredIndex(i)}
            onMouseLeave={() => setHoveredIndex(null)}
            onFocus={() => setHoveredIndex(i)}
            onBlur={() => setHoveredIndex(null)}
          />
        ))}

        {hovered && <Tooltip x={x(times[hoveredIndex])} y={y(values[hoveredIndex])} point={hovered} />}
      </svg>

      <ul className="mt-2 flex flex-wrap gap-4 text-sm text-muted">
        <li>● In range</li>
        <li>▲ Near limit</li>
        <li>◆ Out of limit</li>
      </ul>
    </div>
  )
}
