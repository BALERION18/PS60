import { useAlerts, useAcknowledgeAlert } from '../../hooks/useAlerts'
import { useLanguage } from '../../context/LanguageContext'
import type { AlertOut } from '../../api/hq'

interface Props { stationId: string }

const SEV_COLOR: Record<string, string> = {
  CRITICAL: '#B85A5A',
  HIGH: '#C58A32',
  MEDIUM: '#76804D',
  LOW: '#8A9088',
}

function timeLabel(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false })
  } catch {
    return '—'
  }
}

export default function ActiveAlerts({ stationId }: Props) {
  const { data, isLoading } = useAlerts({ station_id: stationId, ack_state: 'OPEN', page_size: 2 })
  const { mutate: ack, isPending } = useAcknowledgeAlert()
  const { t } = useLanguage()

  const alerts: AlertOut[] = data?.items ?? []

  return (
    <div
      style={{
        background: '#FCFBF8',
        border: '1px solid #DDD8CC',
        borderTop: '3px solid #B85A5A',
        borderRadius: 12,
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Card Header Strip */}
      <div style={{
        padding: '12px 16px 8px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#B85A5A' }}>notifications_active</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#252820', letterSpacing: '0.02em' }}>{t('alerts.title')}</span>
        </div>
        {data && (
          <span style={{ fontSize: 10, color: '#687066', fontWeight: 700 }}>
            {t('alerts.total')}: <span style={{ color: '#B85A5A', background: '#F6F3ED', padding: '1px 5px', borderRadius: 4, border: '1px solid #E9E5DC' }}>{data.total}</span>
          </span>
        )}
      </div>

      <div style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {isLoading && (
          <div style={{ fontSize: 11, color: '#687066', padding: '4px 0' }}>{t('alerts.loading')}</div>
        )}

        {!isLoading && alerts.length === 0 && (
          <div style={{ fontSize: 11, color: '#6F8747', padding: '6px 8px', background: '#E4E8D3', border: '1px solid #C5D4A8', fontWeight: 600, borderRadius: 8 }}>
            ✓ {t('alerts.none')}
          </div>
        )}

        {alerts.map((alert) => (
          <div
            key={alert.alert_id}
            style={{
              background: '#FCFBF8',
              border: '1px solid #E9E5DC',
              borderLeft: `4px solid ${SEV_COLOR[alert.severity] ?? '#8A9088'}`,
              borderRadius: 8,
              padding: '6px 10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
              <span
                style={{
                  fontSize: 8.5,
                  fontWeight: 800,
                  color: '#ffffff',
                  background: SEV_COLOR[alert.severity] ?? '#8A9088',
                  padding: '2px 6px',
                  borderRadius: 4,
                  letterSpacing: '0.04em',
                  flexShrink: 0,
                }}
              >
                {alert.severity}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 9.5, fontWeight: 700, color: '#687066', fontFamily: 'monospace' }}>
                    {timeLabel(alert.triggered_at)} IST
                  </span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#252820' }}>
                    {alert.description}
                  </span>
                </div>
                {alert.asset_id && (
                  <div style={{ fontSize: 9, color: '#687066', marginTop: 1 }}>
                    Asset: {alert.asset_id} • Domain: {alert.domain}
                  </div>
                )}
              </div>
            </div>

            {/* Acknowledge button */}
            <button
              onClick={() => ack({ alertId: alert.alert_id })}
              disabled={isPending}
              title="Acknowledge Alert"
              style={{
                background: '#FCFBF8',
                border: '1px solid #76804D',
                color: '#76804D',
                fontSize: 9,
                fontWeight: 800,
                letterSpacing: '0.04em',
                padding: '3px 8px',
                cursor: 'pointer',
                flexShrink: 0,
                fontFamily: 'Inter',
                transition: 'all 0.15s',
                borderRadius: 4,
                display: 'flex',
                alignItems: 'center',
                gap: 3,
              }}
              onMouseOver={(e) => {
                (e.currentTarget as HTMLElement).style.background = '#76804D'
                ;(e.currentTarget as HTMLElement).style.color = '#ffffff'
              }}
              onMouseOut={(e) => {
                (e.currentTarget as HTMLElement).style.background = '#FCFBF8'
                ;(e.currentTarget as HTMLElement).style.color = '#76804D'
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 12 }}>check</span>
              <span>{t('alerts.ack')}</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
