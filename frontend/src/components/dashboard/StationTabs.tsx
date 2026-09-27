import { useStations } from '../../hooks/useStations'
import { useLanguage } from '../../context/LanguageContext'

interface Props {
  active: string
  onSelect: (s: string) => void
  timeRange?: string
  onTimeRange?: (t: string) => void
}

export default function StationTabs({ active, onSelect }: Props) {
  const { data: stations } = useStations()
  const { t } = useLanguage()

  const maitri = stations?.find((s) => s.station_id === 'maitri')
  const bharati = stations?.find((s) => s.station_id === 'bharati')

  const dotColor = (s: typeof maitri) =>
    !s ? '#94a3b8' : s.link_state === 'UP' ? '#16a34a' : s.link_state === 'DEGRADED' ? '#d97706' : '#dc2626'

  const stateText = (s: typeof maitri) =>
    !s ? 'UNKNOWN' : s.link_state === 'UP' ? t('station.online') : s.link_state === 'DEGRADED' ? t('station.degraded') : t('station.offline')

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 10,
        gap: 12,
        flexWrap: 'wrap',
      }}
    >
      {/* Station Selector Tabs */}
      <div
        style={{
          display: 'flex',
          background: '#ffffff',
          border: '1px solid #cbd5e1',
          boxShadow: '0 1px 2px 0 rgba(0,0,0,0.04)',
          padding: 4,
          gap: 6,
          flex: 1,
        }}
      >
        {[
          {
            id: 'maitri',
            name: t('station.maitri'),
            coords: t('station.maitri_coords'),
            status: maitri,
          },
          {
            id: 'bharati',
            name: t('station.bharati'),
            coords: t('station.bharati_coords'),
            status: bharati,
          },
        ].map(({ id, name, coords, status }) => {
          const isSelected = active === id
          return (
            <button
              key={id}
              onClick={() => onSelect(id)}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                padding: '5px 12px',
                background: isSelected ? '#0b3b60' : '#f8fafc',
                border: isSelected ? '1px solid #0b3b60' : '1px solid #e2e8f0',
                borderLeft: isSelected ? '3px solid #ff9933' : '3px solid transparent',
                cursor: 'pointer',
                fontFamily: 'Inter',
                transition: 'all 0.15s',
                borderRadius: 2,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    className="rounded-full"
                    style={{
                      width: 8,
                      height: 8,
                      background: dotColor(status),
                      display: 'inline-block',
                    }}
                  />
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 800,
                      letterSpacing: '0.02em',
                      color: isSelected ? '#ffffff' : '#0f172a',
                    }}
                  >
                    {name}
                  </span>
                </div>
                {isSelected && (
                  <span
                    style={{
                      fontSize: 8.5,
                      fontWeight: 800,
                      color: '#166534',
                      background: '#dcfce7',
                      border: '1px solid #86efac',
                      padding: '1px 6px',
                      borderRadius: 2,
                    }}
                  >
                    ACTIVE STATION
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 3, fontSize: 10.5, color: isSelected ? '#cbd5e1' : '#64748b' }}>
                <span>{coords}</span>
                <span>•</span>
                <span style={{ color: isSelected ? '#86efac' : '#16a34a', fontWeight: 700 }}>
                  ● {stateText(status)}
                </span>
              </div>
            </button>
          )
        })}
      </div>

    </div>
  )
}
