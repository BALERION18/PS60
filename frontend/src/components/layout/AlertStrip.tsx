import { useAlerts } from '../../hooks/useAlerts'

export default function AlertStrip() {
  const { isError } = useAlerts({ ack_state: 'OPEN', page_size: 1 })

  return (
    <div
      style={{
        background: '#FCFBF8',
        borderBottom: '1px solid #DDD8CC',
        padding: '3px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        minHeight: 34,
        flexShrink: 0,
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}
    >
      {/* Left: Static tagline */}
      <span style={{
        fontSize: 12,
        fontWeight: 700,
        color: '#4F5935',
        letterSpacing: '0.04em',
        fontStyle: 'italic',
      }}>
        Intelligent Monitoring of Maitri &amp; Bharati,&nbsp;
        <span style={{ color: '#C58A32' }}>Anywhere, Anytime</span>
      </span>

      {/* Right: Backend live indicator */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          background: '#F6F3ED',
          border: '1px solid #E9E5DC',
          padding: '2px 10px',
        }}
      >
        <span
          className="pulse-dot rounded-full"
          style={{
            width: 7,
            height: 7,
            background: isError ? '#dc2626' : '#16a34a',
            display: 'inline-block',
          }}
        />
        <span style={{
          fontSize: 10,
          fontWeight: 800,
          color: isError ? '#dc2626' : '#6F8747',
          letterSpacing: '0.04em',
          whiteSpace: 'nowrap',
        }}>
          {isError ? 'BACKEND OFFLINE' : 'VSAT TELEMETRY LIVE'}
        </span>
      </div>
    </div>
  )
}
