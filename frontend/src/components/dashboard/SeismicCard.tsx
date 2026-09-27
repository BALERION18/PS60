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
      color: '#0b3b60',
    },
    {
      icon: 'inventory_2',
      label: 'LOCAL BACKUP',
      value: '30 DAYS',
      sub: 'Zero Data Loss Risk',
      color: '#0b3b60',
    },
    {
      icon: 'cloud_sync',
      label: 'UPLINK SPEED',
      value: '42 kbps',
      sub: 'Hourly Batched Sync',
      color: '#0b3b60',
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
      color: '#0b3b60',
    },
    {
      icon: 'group',
      label: 'WINTER CREW',
      value: '48 ON SITE',
      sub: 'Safe Autonomy: 246 Days',
      color: '#0b3b60',
    },
  ]

  const metrics = viewMode === 'sync' ? syncMetrics : survivalMetrics

  return (
    <div
      style={{
        width: '100%',
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 185,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Official Government Header Strip */}
      <div
        style={{
          background: '#0b3b60',
          borderBottom: '2px solid #ff9933',
          padding: '6px 12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0, flex: 1 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#ff9933', flexShrink: 0 }}>
            {viewMode === 'sync' ? 'satellite_alt' : 'shield_with_heart'}
          </span>
          <span
            style={{
              fontSize: 11.5,
              fontWeight: 800,
              color: '#ffffff',
              letterSpacing: '0.04em',
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
              background: 'rgba(255, 255, 255, 0.15)',
              border: '1px solid rgba(255, 255, 255, 0.35)',
              color: '#ffffff',
              padding: '2px 6px',
              cursor: 'pointer',
              borderRadius: 2,
              whiteSpace: 'nowrap',
            }}
          >
            {viewMode === 'sync' ? 'SURVIVAL' : 'SATELLITE'}
          </button>
          <span
            style={{
              fontSize: 8.5,
              color: '#ffedd5',
              background: 'rgba(255, 153, 51, 0.25)',
              border: '1px solid rgba(255, 153, 51, 0.5)',
              padding: '1px 6px',
              fontWeight: 800,
              borderRadius: 2,
              whiteSpace: 'nowrap',
            }}
          >
            {viewMode === 'sync' ? 'ISRO GSAT-30' : 'MoES / NCPOR'}
          </span>
        </div>
      </div>

      {/* Official Government 4-Tile Parameter Grid (Matches MetMastCard) */}
      <div
        style={{
          flex: 1,
          padding: '10px 12px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          background: '#f8fafc',
        }}
      >
        {metrics.map(({ icon, label, value, sub, color }) => (
          <div
            key={label}
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              padding: '7px 10px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
              <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.04em', color: '#64748b' }}>
                {label}
              </span>
              <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#94a3b8' }}>
                {icon}
              </span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 800, color, fontFamily: 'Inter', letterSpacing: '-0.01em' }}>
              {value}
            </div>
            <div style={{ fontSize: 8.5, fontWeight: 600, color: '#64748b', marginTop: 1 }}>
              {sub}
            </div>
          </div>
        ))}
      </div>

      {/* Official Government Verification Strip */}
      <div
        style={{
          background: '#f1f5f9',
          borderTop: '1px solid #e2e8f0',
          padding: '4px 10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 8.5,
          color: '#475569',
        }}
      >
        <span>
          {viewMode === 'sync'
            ? `● DTN Polar Store & Forward • ${stationName}`
            : `● 45th Expedition • Winter Lockout Ready`}
        </span>
        <span style={{ color: '#15803d', fontWeight: 700 }}>
          {viewMode === 'sync' ? '✓ ISRO Verified' : '✓ Resources Safe'}
        </span>
      </div>
    </div>
  )
}
