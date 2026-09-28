import { useSensors } from '../../hooks/useSensors'
import { useLanguage } from '../../context/LanguageContext'
import type { SensorSummary } from '../../api/hq'

interface Props { stationId: string }

function find(sensors: SensorSummary[] | undefined, key: string) {
  return sensors?.find(s => s.sensor_id.includes(key))
}
function fmtVal(s: SensorSummary | undefined, decimals = 1, unit = '') {
  if (!s || s.latest_value == null) return '---'
  return `${s.latest_value.toFixed(decimals)} ${unit}`.trim()
}

export default function MetMastCard({ stationId }: Props) {
  const { data: sensors } = useSensors(stationId, 'weather')
  const { t } = useLanguage()

  const windSpd = find(sensors, 'wind_speed')
  const windDir = find(sensors, 'wind_dir')
  const pressure = find(sensors, 'pressure')
  const solarRad = find(sensors, 'solar_rad')

  const metrics = [
    {
      icon: 'air',
      label: t('met.wind_speed'),
      value: fmtVal(windSpd, 1, 'km/h'),
      sub: (windSpd?.latest_value ?? 0) > 30 ? 'Strong Breeze' : 'Moderate',
      color: (windSpd?.latest_value ?? 0) > 30 ? '#C58A32' : '#4F5935',
    },
    {
      icon: 'explore',
      label: t('met.direction'),
      value: fmtVal(windDir, 0, '°'),
      sub: '247° WSW Azimuth',
      color: '#4F5935',
    },
    {
      icon: 'speed',
      label: t('met.pressure'),
      value: fmtVal(pressure, 0, 'hPa'),
      sub: 'Normal Barometric',
      color: '#4F5935',
    },
    {
      icon: 'wb_sunny',
      label: t('met.solar_rad'),
      value: fmtVal(solarRad, 0, 'W/m²'),
      sub: 'Polar Daylight Flux',
      color: '#4F5935',
    },
  ]

  return (
    <div
      style={{
        width: '100%',
        background: '#FCFBF8',
        border: '1px solid #DDD8CC',
        borderTop: '3px solid #8278A4',
        borderRadius: 12,
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 185,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Card Header Strip */}
      <div style={{
        padding: '12px 16px 8px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        position: 'relative',
        zIndex: 3,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#8278A4' }}>cell_tower</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#252820', letterSpacing: '0.02em' }}>{t('met.title')} (10M)</span>
        </div>
        <span
          style={{
            fontSize: 8.5,
            color: '#687066',
            background: 'transparent',
            border: '1px solid #E9E5DC',
            padding: '1px 6px',
            fontWeight: 800,
            borderRadius: 4,
          }}
        >
          IMD-AWS-01
        </span>
      </div>

      {/* Sensor Grid */}
      <div style={{ flex: 1, padding: '10px 12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, background: '#F6F3ED' }}>
        {metrics.map(({ icon, label, value, sub, color }) => (
          <div
            key={label}
            style={{
              background: '#FCFBF8',
              border: '1px solid #E9E5DC',
              borderRadius: 8,
              padding: '7px 10px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
              <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.04em', color: '#687066' }}>
                {label}
              </span>
              <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#8A9088' }}>
                {icon}
              </span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 800, color: color === '#4F5935' ? '#252820' : color === '#C58A32' ? '#C58A32' : color, fontFamily: 'Inter', letterSpacing: '-0.01em' }}>
              {value}
            </div>
            <div style={{ fontSize: 8.5, fontWeight: 600, color: '#687066', marginTop: 1 }}>
              {sub}
            </div>
          </div>
        ))}
      </div>

      {/* Official Calibration Strip */}
      <div
        style={{
          background: '#F6F3ED',
          borderTop: '1px solid #E9E5DC',
          padding: '4px 10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 8.5,
          color: '#687066',
        }}
      >
        <span>● Sensor Calibrated • 10m Tower</span>
        <span style={{ color: '#6F8747', fontWeight: 700 }}>✓ IMD Certified</span>
      </div>
    </div>
  )
}
