interface Props {
  value: number        // 0–100
  color?: string
  label: string
  size?: number
}

export default function GaugeCircle({ value, color = '#0284c7', label, size = 52 }: Props) {
  const r = 15.9
  const dash = Math.min(100, Math.max(0, value))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg viewBox="0 0 36 36" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
          <circle cx="18" cy="18" r={r} fill="none" stroke="#e2e8f0" strokeWidth="3.2" />
          <circle
            cx="18" cy="18" r={r} fill="none" stroke={color} strokeWidth="3.2"
            strokeDasharray={`${dash} 100`} strokeLinecap="butt"
          />
        </svg>
        <span style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: 11, fontWeight: 800, color: '#0f172a', fontFamily: 'Inter',
        }}>
          {Math.round(value)}%
        </span>
      </div>
      <span style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.04em', color: '#475569' }}>
        {label}
      </span>
    </div>
  )
}
