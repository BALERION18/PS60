/** Simple SVG sparkline for fuel level or any 0–100 time series */
interface Props {
  values?: number[]       // array of 0–100 values
  color?: string
  label?: string
}

export default function FuelSparkline({ values, color = '#ea580c', label = 'FUEL LVL' }: Props) {
  // Default fallback data if API not available yet
  const pts = values && values.length > 0
    ? values
    : [40, 38, 34, 36, 28, 22, 18, 15, 12]

  const W = 200
  const H = 60
  const xStep = W / (pts.length - 1)

  // Map value (0–100) → y (0=top, H=bottom) — invert so high value = high line
  const toY = (v: number) => H - (v / 100) * H

  const pointStr = pts.map((v, i) => `${i * xStep},${toY(v)}`).join(' ')

  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 56, borderBottom: '1px solid #e2e8f0', borderLeft: '1px solid #e2e8f0', background: '#f8fafc', padding: '4px' }}>
      <span style={{ position: 'absolute', top: 3, right: 6, fontSize: 9.5, fontWeight: 700, color: '#334155', letterSpacing: '0.04em', zIndex: 2 }}>
        {label}
      </span>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {/* Grid */}
        <line x1="0" y1="20" x2={W} y2="20" stroke="#e2e8f0" strokeWidth="1" />
        <line x1="0" y1="40" x2={W} y2="40" stroke="#e2e8f0" strokeWidth="1" />
        <line x1="50" y1="0" x2="50" y2={H} stroke="#e2e8f0" strokeWidth="1" />
        <line x1="100" y1="0" x2="100" y2={H} stroke="#e2e8f0" strokeWidth="1" />
        <line x1="150" y1="0" x2="150" y2={H} stroke="#e2e8f0" strokeWidth="1" />
        {/* Line */}
        <polyline
          points={pointStr}
          fill="none" stroke={color} strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round"
        />
        {/* Latest value dot */}
        {pts.length > 0 && (
          <circle
            cx={(pts.length - 1) * xStep}
            cy={toY(pts[pts.length - 1])}
            r="3" fill={color}
          />
        )}
      </svg>
    </div>
  )
}
