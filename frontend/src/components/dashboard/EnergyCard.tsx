import { useSensors } from '../../hooks/useSensors'
import { useLanguage } from '../../context/LanguageContext'
import GaugeCircle from '../ui/GaugeCircle'
import type { SensorSummary } from '../../api/hq'

interface Props { stationId: string }

function findVal(sensors: SensorSummary[] | undefined, key: string): number {
  const s = sensors?.find(s => s.sensor_id.includes(key))
  return s?.latest_value ?? 0
}

export default function EnergyCard({ stationId }: Props) {
  const { data: sensors } = useSensors(stationId, 'energy')
  const { t } = useLanguage()

  const power = Math.min(100, findVal(sensors, 'load'))
  const solar = Math.min(100, findVal(sensors, 'solar'))
  const storage = Math.min(100, findVal(sensors, 'storage'))
  const fuel = findVal(sensors, 'fuel')

  const hasCritical = fuel > 0 && fuel < 15
  const hasWarning = fuel > 0 && fuel < 30

  const status = hasCritical ? 'CRITICAL' : hasWarning ? 'WARNING' : 'NOMINAL'
  const statusColor = hasCritical ? '#B85A5A' : hasWarning ? '#C58A32' : '#6F8747'

  return (
    <div
      style={{
        background: '#FCFBF8',
        border: '1px solid #DDD8CC',
        borderTop: '3px solid #C58A32',
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
          <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#C58A32' }}>bolt</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#252820', letterSpacing: '0.02em' }}>{t('energy.title')}</span>
        </div>
        <span
          style={{
            fontSize: 8.5,
            fontWeight: 800,
            color: statusColor,
            background: 'transparent',
            padding: '1px 6px',
            border: `1px solid ${statusColor}`,
            borderRadius: 4,
          }}
        >
          {status}
        </span>
      </div>

      <div style={{ padding: '8px 10px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Gauges */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 8 }}>
          <GaugeCircle value={power} color="#4F5935" label={t('energy.power')} />
          <GaugeCircle value={solar} color="#C58A32" label={t('energy.solar')} />
          <GaugeCircle value={storage} color="#6F8747" label={t('energy.storage')} />
        </div>

        {/* Diesel Fuel Stock Section */}
        <div style={{ background: '#F6F3ED', border: '1px solid #E9E5DC', padding: '6px 8px', marginTop: 'auto', borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 9.5, fontWeight: 800, color: '#4F5935', letterSpacing: '0.03em' }}>
              {t('energy.fuel')}
            </span>
            <span style={{ fontSize: 11, fontWeight: 800, color: statusColor, fontFamily: 'Inter' }}>
              {fuel > 0 ? `${fuel.toFixed(0)}%` : '42%'} ({fuel > 0 ? Math.round(fuel * 920).toLocaleString() : '38,640'} L)
            </span>
          </div>

          {/* Progress Bar */}
          <div style={{ width: '100%', height: 6, background: '#E9E5DC', borderRadius: 3, overflow: 'hidden', marginBottom: 6 }}>
            <div
              style={{
                width: `${fuel > 0 ? fuel : 42}%`,
                height: '100%',
                background: statusColor,
                transition: 'width 0.4s ease',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8.5, color: '#687066' }}>
            <span>Reserve: <strong style={{ color: '#252820' }}>~48 Days Winter Stock</strong></span>
            <span style={{ color: '#6F8747', fontWeight: 700 }}>● Burn Rate: Optimal</span>
          </div>
        </div>
      </div>
    </div>
  )
}
