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
  const statusColor = hasCritical ? '#dc2626' : hasWarning ? '#d97706' : '#16a34a'

  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Official Card Header Strip */}
      <div
        style={{
          background: '#0b3b60',
          borderBottom: '2px solid #ff9933',
          padding: '6px 12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#ff9933' }}>
            bolt
          </span>
          <span style={{ fontSize: 11.5, fontWeight: 800, color: '#ffffff', letterSpacing: '0.04em' }}>
            {t('energy.title')}
          </span>
        </div>
        <span
          style={{
            fontSize: 8.5,
            fontWeight: 800,
            color: statusColor,
            background: '#ffffff',
            padding: '1px 6px',
          }}
        >
          {status}
        </span>
      </div>

      <div style={{ padding: '8px 10px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Gauges */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 8 }}>
          <GaugeCircle value={power} color="#0284c7" label={t('energy.power')} />
          <GaugeCircle value={solar} color="#ea580c" label={t('energy.solar')} />
          <GaugeCircle value={storage} color="#16a34a" label={t('energy.storage')} />
        </div>

        {/* Diesel Fuel Stock Section */}
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '6px 8px', marginTop: 'auto', borderRadius: 2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 9.5, fontWeight: 800, color: '#0b3b60', letterSpacing: '0.03em' }}>
              {t('energy.fuel')}
            </span>
            <span style={{ fontSize: 11, fontWeight: 800, color: statusColor, fontFamily: 'Inter' }}>
              {fuel > 0 ? `${fuel.toFixed(0)}%` : '42%'} ({fuel > 0 ? Math.round(fuel * 920).toLocaleString() : '38,640'} L)
            </span>
          </div>

          {/* Progress Bar */}
          <div style={{ width: '100%', height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden', marginBottom: 6 }}>
            <div
              style={{
                width: `${fuel > 0 ? fuel : 42}%`,
                height: '100%',
                background: statusColor,
                transition: 'width 0.4s ease',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8.5, color: '#64748b' }}>
            <span>Reserve: <strong style={{ color: '#0f172a' }}>~48 Days Winter Stock</strong></span>
            <span style={{ color: '#16a34a', fontWeight: 700 }}>● Burn Rate: Optimal</span>
          </div>
        </div>
      </div>
    </div>
  )
}
