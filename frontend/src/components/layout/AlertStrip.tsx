import { useAlerts } from '../../hooks/useAlerts'
import { useLanguage } from '../../context/LanguageContext'

export default function AlertStrip() {
  const { data, isError } = useAlerts({ ack_state: 'OPEN', page_size: 10 })
  const { t } = useLanguage()

  const alerts = data?.items ?? []

  const bulletins = [
    t('marquee.notice1'),
    alerts.length > 0
      ? alerts.map(a => `[${a.severity}] ${a.station_id.toUpperCase()}: ${a.description}`).join(' • ')
      : t('advisory.all_nominal'),
    t('marquee.notice2'),
    'NCPOR HQ Goa Polar Satellite Telemetry Uplink: GSAT-7 / Inmarsat Encrypted Multi-Beam Nominal',
  ]

  // Render a block of bulletins
  const renderBulletinBlock = () => (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 24, paddingRight: 24 }}>
      {bulletins.map((item, idx) => (
        <span key={idx} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 11, fontWeight: 600, color: '#1e293b' }}>
          <span style={{ color: '#ea580c', fontWeight: 900 }}>★</span>
          <span>{item}</span>
        </span>
      ))}
    </div>
  )

  return (
    <div
      style={{
        background: '#ffffff',
        borderBottom: '1px solid #cbd5e1',
        padding: '3px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        minHeight: 34,
        flexShrink: 0,
        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
        overflow: 'hidden',
      }}
    >
      {/* Official Government "LATEST BULLETINS" Badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          background: '#dc2626',
          padding: '3px 10px',
          flexShrink: 0,
          boxShadow: '0 1px 2px rgba(220,38,38,0.25)',
          zIndex: 5,
        }}
      >
        <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#ffffff' }}>
          campaign
        </span>
        <span style={{ fontSize: 10, fontWeight: 900, letterSpacing: '0.06em', color: '#ffffff', whiteSpace: 'nowrap' }}>
          {t('marquee.label')}
        </span>
      </div>

      {/* Running Continuous Marquee Ticker */}
      <div
        style={{
          flex: 1,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
        }}
        title="Hover to pause ticker / स्क्रॉल रोकने के लिए कर्सर ऊपर लाएं"
      >
        <div className="marquee-track">
          {renderBulletinBlock()}
          {renderBulletinBlock()}
        </div>
      </div>

      {/* Live sync pulse */}
      <div
        style={{
          marginLeft: 'auto',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          flexShrink: 0,
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          padding: '2px 8px',
          zIndex: 5,
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
        <span style={{ fontSize: 10, fontWeight: 800, color: isError ? '#dc2626' : '#166534', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>
          {isError ? 'LINK OFFLINE' : t('advisory.live')}
        </span>
      </div>
    </div>
  )
}
