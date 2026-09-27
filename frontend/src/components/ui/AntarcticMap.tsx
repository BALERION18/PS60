interface Props {
  maitriOnline: boolean
  bharatiOnline: boolean
  activeStation: string
}

export default function AntarcticMap({ maitriOnline, bharatiOnline, activeStation }: Props) {
  return (
    <div style={{ border: '1px solid #cbd5e1', overflow: 'hidden', position: 'relative', background: '#f8fafc', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
      <svg viewBox="0 0 200 130" style={{ width: '100%', display: 'block' }} xmlns="http://www.w3.org/2000/svg">
        <rect width="200" height="130" fill="#f8fafc" />
        <ellipse cx="100" cy="72" rx="70" ry="52" fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1" />
        <ellipse cx="82" cy="58" rx="42" ry="30" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="0.5" />
        <path d="M30 72 Q50 90 70 85 Q90 95 110 88 Q130 93 150 78 Q165 70 165 72 Q160 95 100 110 Q50 108 30 88 Z" fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="0.5" />
        {/* Maitri */}
        <circle cx="85" cy="68" r="4" fill={maitriOnline ? '#16a34a' : '#94a3b8'}
          stroke="#ffffff" strokeWidth="1"
          opacity={activeStation === 'maitri' ? 1 : 0.7} />
        <text x="89" y="65" fill={activeStation === 'maitri' ? '#0b3b60' : '#475569'} fontSize="8.5" fontFamily="Inter" fontWeight="800">
          मैत्री (Maitri)
        </text>
        {/* Bharati */}
        <circle cx="118" cy="82" r="4" fill={bharatiOnline ? '#16a34a' : '#94a3b8'}
          stroke="#ffffff" strokeWidth="1"
          opacity={activeStation === 'bharati' ? 1 : 0.7} />
        <text x="122" y="86" fill={activeStation === 'bharati' ? '#0b3b60' : '#475569'} fontSize="8.5" fontFamily="Inter" fontWeight="800">
          भारती (Bharati)
        </text>
        <text x="75" y="45" fill="#64748b" fontSize="7.5" fontFamily="Inter" fontWeight="700">SOUTH POLE (दक्षिण ध्रुव)</text>
        <circle cx="100" cy="40" r="2" fill="none" stroke="#64748b" strokeWidth="1" />
        <circle cx="100" cy="72" r="40" fill="none" stroke="#cbd5e1" strokeWidth="0.5" strokeDasharray="3,4" />
        <circle cx="100" cy="72" r="60" fill="none" stroke="#cbd5e1" strokeWidth="0.5" strokeDasharray="3,4" />
      </svg>
    </div>
  )
}
