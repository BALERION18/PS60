import { useDashboard } from '../../hooks/useDashboard'
import { useQuery } from '@tanstack/react-query'
import { useLanguage } from '../../context/LanguageContext'
import { getHealth } from '../../api/hq'

export default function Footer() {
  const { data: dash } = useDashboard()
  const { t } = useLanguage()
  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: 0,
  })

  const online = !isError && health?.status === 'ok'

  return (
    <footer
      style={{
        background: '#0b3b60',
        color: '#ffffff',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        marginTop: 'auto',
        position: 'relative',
        zIndex: 10,
      }}
    >
      {/* ── National Tricolour Accent Line ── */}
      <div className="tricolour-bottom" />

      {/* ── Tier 1: Government Portal Links Ribbon ── */}
      <div
        style={{
          background: '#082842',
          borderBottom: '1px solid #0f3d63',
          padding: '6px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
          fontSize: 10.5,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#ffedd5', fontWeight: 700 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#ff9933' }}>link</span>
          <span>{t('footer.quick_links')}:</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          {[
            { label: t('footer.link_moes'), url: 'https://www.moes.gov.in' },
            { label: t('footer.link_imd'), url: 'https://mausam.imd.gov.in' },
            { label: t('footer.link_digital_india'), url: 'https://www.digitalindia.gov.in' },
          ].map((item, i) => (
            <a
              key={i}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: '#cbd5e1',
                textDecoration: 'none',
                transition: 'color 0.15s',
              }}
              onMouseOver={(e) => ((e.currentTarget as HTMLElement).style.color = '#ff9933')}
              onMouseOut={(e) => ((e.currentTarget as HTMLElement).style.color = '#cbd5e1')}
            >
              {item.label}
            </a>
          ))}
        </div>
      </div>


      {/* ── Tier 3: Official Ownership & Telemetry ── */}
      <div
        style={{
          background: '#072138',
          padding: '8px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        {/* Left: NCPOR Logo + Official Ministry Copyright */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <img src="/ncpor_logo.png" alt="NCPOR Logo" style={{ height: 32, width: 32, objectFit: 'contain' }} />
          <div style={{ fontSize: 10, color: '#cbd5e1', lineHeight: 1.3 }}>
            <div>
              <span style={{ fontWeight: 800, color: '#ffffff' }}>
                {t('footer.copyright')}
              </span>
              <span style={{ color: '#64748b', margin: '0 6px' }}>|</span>
              <span>{t('footer.ministry')}</span>
            </div>
            <div style={{ color: '#94a3b8', fontSize: 9.5 }}>
              {t('footer.designed_by')}
            </div>
          </div>
        </div>

        {/* Right: Real-time Telemetry Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 10, color: '#cbd5e1' }}>
          {dash && (
            <span>
              {t('footer.open_alerts')}:{' '}
              <strong style={{ color: dash.total_open_alerts > 0 ? '#fca5a5' : '#86efac' }}>
                {dash.total_open_alerts}
              </strong>
            </span>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ fontWeight: 700, color: online ? '#86efac' : '#fca5a5' }}>
              {t('footer.hq_server')}: {online ? t('footer.connected') : 'OFFLINE'}
            </span>
            <span
              className="pulse-dot rounded-full"
              style={{
                width: 6,
                height: 6,
                background: online ? '#10b981' : '#ef4444',
                display: 'inline-block',
              }}
            />
          </div>
        </div>
      </div>
    </footer>
  )
}
