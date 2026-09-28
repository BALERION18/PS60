import { useSensors } from '../../hooks/useSensors'
import { useLanguage } from '../../context/LanguageContext'
import type { SensorSummary } from '../../api/hq'

interface Props { stationId: string }

function fmt(s: SensorSummary | undefined, unit = '') {
  if (!s || s.latest_value == null) return '---'
  return `${s.latest_value.toFixed(1)}${unit}`
}

export default function WeatherCard({ stationId }: Props) {
  const { data: maitriSensors } = useSensors('maitri', 'weather')
  const { data: bharatiSensors } = useSensors('bharati', 'weather')
  const { t } = useLanguage()

  const find = (sensors: SensorSummary[] | undefined, key: string) =>
    sensors?.find(s => s.sensor_id.includes(key))

  const mTemp = find(maitriSensors, 'temp')
  const mWind = find(maitriSensors, 'wind_speed')
  const mWDir = find(maitriSensors, 'wind_dir')
  const bTemp = find(bharatiSensors, 'temp')
  const bWind = find(bharatiSensors, 'wind_speed')
  const bWDir = find(bharatiSensors, 'wind_dir')

  const isMaitriActive = stationId === 'maitri'

  return (
    <div
      style={{
        background: '#FCFBF8',
        border: '1px solid #DDD8CC',
        borderTop: '3px solid #6F8747',
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
          <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#6F8747' }}>thermostat</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#252820', letterSpacing: '0.02em' }}>{t('weather.title')}</span>
        </div>
        <span
          style={{
            fontSize: 8.5,
            fontWeight: 800,
            background: 'transparent',
            border: '1px solid #E9E5DC',
            color: '#687066',
            padding: '1px 6px',
            borderRadius: 4,
          }}
        >
          IMD METEOROLOGY
        </span>
      </div>

      <div style={{ padding: '8px 10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        {/* Maitri */}
        <div
          style={{
            padding: '6px 8px',
            background: isMaitriActive ? '#E4E8D3' : '#F6F3ED',
            border: isMaitriActive ? '1.5px solid #76804D' : '1px solid #E9E5DC',
            borderRadius: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
            <span style={{ fontSize: 9.5, fontWeight: 800, color: isMaitriActive ? '#4F5935' : '#687066' }}>
              {t('station.maitri')}
            </span>
            {isMaitriActive && (
              <span style={{ fontSize: 7, fontWeight: 800, color: '#4F5935', background: '#FCFBF8', padding: '1px 4px', borderRadius: 2 }}>
                ACTIVE
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 2, marginBottom: 2 }}>
            <span style={{ fontSize: 20, fontWeight: 800, color: '#252820', letterSpacing: '-0.02em' }}>
              {fmt(mTemp, '°')}
            </span>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#C58A32' }}>C</span>
          </div>
          <div style={{ fontSize: 9.5, fontWeight: 600, color: '#687066', lineHeight: 1.25 }}>
            {t('weather.wind')}: <span style={{ color: '#252820', fontWeight: 700 }}>{fmt(mWind, ' km/h')}</span>{mWDir?.latest_value != null ? ` (${mWDir.latest_value.toFixed(0)}°)` : ''}
          </div>
          <div style={{ fontSize: 8.5, color: '#8A9088', marginTop: 2 }}>
            Chill: <strong style={{ color: '#8278A4' }}>-28°C</strong> • Clear
          </div>
        </div>

        {/* Bharati */}
        <div
          style={{
            padding: '6px 8px',
            background: !isMaitriActive ? '#E4E8D3' : '#F6F3ED',
            border: !isMaitriActive ? '1.5px solid #76804D' : '1px solid #E9E5DC',
            borderRadius: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
            <span style={{ fontSize: 9.5, fontWeight: 800, color: !isMaitriActive ? '#4F5935' : '#687066' }}>
              {t('station.bharati')}
            </span>
            {!isMaitriActive && (
              <span style={{ fontSize: 7, fontWeight: 800, color: '#4F5935', background: '#FCFBF8', padding: '1px 4px', borderRadius: 2 }}>
                ACTIVE
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 2, marginBottom: 2 }}>
            <span style={{ fontSize: 20, fontWeight: 800, color: '#252820', letterSpacing: '-0.02em' }}>
              {fmt(bTemp, '°')}
            </span>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#C58A32' }}>C</span>
          </div>
          <div style={{ fontSize: 9.5, fontWeight: 600, color: '#687066', lineHeight: 1.25 }}>
            {t('weather.wind')}: <span style={{ color: '#252820', fontWeight: 700 }}>{fmt(bWind, ' km/h')}</span>{bWDir?.latest_value != null ? ` (${bWDir.latest_value.toFixed(0)}°)` : ''}
          </div>
          <div style={{ fontSize: 8.5, color: '#8A9088', marginTop: 2 }}>
            Chill: <strong style={{ color: '#8278A4' }}>-19°C</strong> • Snow
          </div>
        </div>
      </div>

      {/* Advisory Status Footer */}
      <div
        style={{
          background: '#F6F3ED',
          borderTop: '1px solid #E9E5DC',
          padding: '4px 10px',
          fontSize: 8.5,
          color: '#687066',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottomLeftRadius: 12,
          borderBottomRightRadius: 12,
        }}
      >
        <span>● IMD Polar Advisory: Normal Operations</span>
        <span style={{ color: '#6F8747', fontWeight: 700 }}>✓ No Blizzard Warning</span>
      </div>
    </div>
  )
}
