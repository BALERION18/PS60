import { useState } from 'react'

interface Props {
  stationId: string
}

export default function SeismicCard({ stationId }: Props) {
  const [viewMode, setViewMode] = useState<'sync' | 'autonomy'>('sync')

  const isMaitri = stationId === 'maitri'
  const stationName = isMaitri ? 'Maitri Base' : 'Bharati Base'

  const syncMetrics = [
    {
      icon: 'satellite_alt',
      label: 'SATELLITE LINK',
      value: 'ONLINE',
      sub: 'ISRO GSAT-30 (574ms)',
      color: '#16a34a',
    },
    {
      icon: 'compress',
      label: 'DATA COMPRESSION',
      value: '88.2% SAVED',
      sub: '8.4x Compacted at Edge',
      color: '#4F5935',
    },
    {
      icon: 'inventory_2',
      label: 'LOCAL BACKUP',
      value: '30 DAYS',
      sub: 'Zero Data Loss Risk',
      color: '#4F5935',
    },
    {
      icon: 'cloud_sync',
      label: 'UPLINK SPEED',
      value: '42 kbps',
      sub: 'Hourly Batched Sync',
      color: '#4F5935',
    },
  ]

  const survivalMetrics = [
    {
      icon: 'local_gas_station',
      label: 'DIESEL FUEL',
      value: '48 DAYS',
      sub: '42% Remaining (Genset)',
      color: '#16a34a',
    },
    {
      icon: 'water_drop',
      label: 'FRESHWATER',
      value: '12 DAYS',
      sub: isMaitri ? '88% Lake Priyadarshini' : '84% Desalination',
      color: '#0284c7',
    },
    {
      icon: 'restaurant',
      label: 'FOOD RATIONS',
      value: '290 DAYS',
      sub: '95% Winter Supply',
      color: '#4F5935',
    },
    {
      icon: 'group',
      label: 'WINTER CREW',
      value: '48 ON SITE',
      sub: 'Safe Autonomy: 246 Days',
      color: '#4F5935',
    },
  ]

  const metrics = viewMode === 'sync' ? syncMetrics : survivalMetrics

  return (
    <div
      style={{
        width: '100%',
        background: '#FCFBF8',
        border: '1px solid #DDD8CC',
        borderTop: '3px solid #4F5935',
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
        gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#4F5935', flexShrink: 0 }}>
            {viewMode === 'sync' ? 'satellite_alt' : 'shield_with_heart'}
          </span>
          <span
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: '#252820',
              letterSpacing: '0.02em',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {viewMode === 'sync' ? 'SATELLITE & DATA LINK' : 'WINTER SURVIVAL HORIZON'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <button
            onClick={() => setViewMode(m => m === 'sync' ? 'autonomy' : 'sync')}
            title="Switch View"
            style={{
              fontSize: 8.5,
              fontWeight: 800,
              background: '#F6F3ED',
              border: '1px solid #E9E5DC',
              color: '#687066',
              padding: '2px 6px',
              cursor: 'pointer',
              borderRadius: 4,
              whiteSpace: 'nowrap',
            }}
          >
            {viewMode === 'sync' ? 'SURVIVAL' : 'SATELLITE'}
          </button>
          <span
            style={{
              fontSize: 8.5,
              color: '#4F5935',
              background: '#E4E8D3',
              border: '1px solid #C5D4A8',
              padding: '1px 6px',
              fontWeight: 800,
              borderRadius: 4,
              whiteSpace: 'nowrap',
            }}
          >
            {viewMode === 'sync' ? 'ISRO GSAT-30' : 'MoES / NCPOR'}
          </span>
        </div>
      </div>

      {/* Grid */}
      <div
        style={{
          flex: 1,
          padding: '10px 12px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          background: '#F6F3ED',
        }}
      >
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
            <div style={{ fontSize: 15, fontWeight: 800, color: color === '#16a34a' ? '#6F8747' : color === '#0284c7' ? '#8278A4' : color === '#4F5935' ? '#4F5935' : color, fontFamily: 'Inter', letterSpacing: '-0.01em' }}>
              {value}
            </div>
            <div style={{ fontSize: 8.5, fontWeight: 600, color: '#687066', marginTop: 1 }}>
              {sub}
            </div>
          </div>
        ))}
      </div>

      {/* Official Government Verification Strip */}
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
        <span>
          {viewMode === 'sync'
            ? `● DTN Polar Store & Forward • ${stationName}`
            : `● 45th Expedition • Winter Lockout Ready`}
        </span>
        <span style={{ color: '#6F8747', fontWeight: 700 }}>
          {viewMode === 'sync' ? '✓ ISRO Verified' : '✓ Resources Safe'}
        </span>
      </div>
    </div>
  )
}
