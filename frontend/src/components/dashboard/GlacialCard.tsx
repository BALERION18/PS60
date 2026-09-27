import { useState } from 'react'
import { useLanguage } from '../../context/LanguageContext'

interface Props {
  stationId?: string
}

export default function GlacialCard({ stationId = 'maitri' }: Props) {
  const { t } = useLanguage()
  const [viewMode, setViewMode] = useState<'gpr' | 'lss'>('lss')

  const isMaitri = stationId === 'maitri'

  // Plain-English values for LSS view
  const lssData = isMaitri
    ? {
        source: 'Water from Lake Priyadarshini (Warm Pipe)',
        reserveL: '14,800 Litres',
        percent: 88,
        days: '12 Days Left',
        heatState: 'ON (Water Flows)',
        habitatTemp: '+19.2°C',
        habitatZone: 'Bedrooms (Warm & Safe)',
        airO2: 'Safe (20.9% O₂)',
        airSub: 'Clean air to breathe',
        division: 'Station Life Support Active',
      }
    : {
        source: 'Clean Water from Sea Desalination Plant',
        reserveL: '11,200 Litres',
        percent: 84,
        days: '9 Days Left',
        heatState: 'ON (Water Flows)',
        habitatTemp: '+20.1°C',
        habitatZone: 'Bedrooms (Warm & Safe)',
        airO2: 'Safe (20.9% O₂)',
        airSub: 'Clean air to breathe',
        division: 'Station Life Support Active',
      }

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
      }}
    >
      {/* Official Government Header Strip */}
      <div
        style={{
          background: '#0b3b60',
          borderBottom: '2px solid #ff9933',
          padding: '6px 10px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 8,
          overflow: 'hidden',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0, flex: 1 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#ff9933', flexShrink: 0 }}>
            {viewMode === 'gpr' ? 'radar' : 'water_drop'}
          </span>
          <span
            style={{
              fontSize: 11.5,
              fontWeight: 800,
              color: '#ffffff',
              letterSpacing: '0.03em',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {viewMode === 'gpr' ? 'ICE RADAR SCAN' : t('lss.title')}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
          <button
            onClick={() => setViewMode(m => m === 'gpr' ? 'lss' : 'gpr')}
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
            {viewMode === 'gpr' ? 'WATER' : 'RADAR'}
          </button>
          <span
            style={{
              fontSize: 8.5,
              color: '#ffedd5',
              background: 'rgba(255, 153, 51, 0.25)',
              border: '1px solid rgba(255, 153, 51, 0.5)',
              padding: '1px 5px',
              fontWeight: 800,
              borderRadius: 2,
              whiteSpace: 'nowrap',
            }}
          >
            ACTIVE
          </span>
        </div>
      </div>

      {viewMode === 'gpr' ? (
        /* ── OFFICIAL GOVERNMENT SCIENTIFIC GRAPH (Light Theme, Clear Grid & Labels) ── */
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#ffffff' }}>
          {/* Government Legend Ribbon */}
          <div
            style={{
              background: '#f8fafc',
              borderBottom: '1px solid #e2e8f0',
              padding: '5px 10px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: 9.5,
              color: '#334155',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 4, background: '#0284c7', display: 'inline-block' }} />
                <span>Surface Snow (0–15m)</span>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 4, background: '#0369a1', display: 'inline-block' }} />
                <span>Solid Ice (15–142m)</span>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 4, background: '#ea580c', display: 'inline-block' }} />
                <span>Bedrock (142m)</span>
              </span>
            </div>
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
              ✓ NO DANGER CRACKS
            </span>
          </div>

          {/* Clean Scientific Graph Canvas (Government Standard Light Paper Format) */}
          <div style={{ flex: 1, position: 'relative', minHeight: 92, background: '#f8fafc', borderBottom: '1px solid #e2e8f0', overflow: 'hidden' }}>
            <svg style={{ width: '100%', height: '100%' }} viewBox="0 0 320 88" preserveAspectRatio="none">
              <defs>
                {/* Government Grid Pattern */}
                <pattern id="radar-grid" width="30" height="20" patternUnits="userSpaceOnUse">
                  <path d="M 30 0 L 0 0 0 20" fill="none" stroke="#e2e8f0" strokeWidth="0.8" />
                </pattern>
                {/* Surface Snow Tint */}
                <linearGradient id="gov-snow-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#bae6fd" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#bae6fd" stopOpacity="0.2" />
                </linearGradient>
                {/* Solid Ice Tint */}
                <linearGradient id="gov-ice-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#e0f2fe" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#bae6fd" stopOpacity="0.4" />
                </linearGradient>
                {/* Bedrock Fill */}
                <linearGradient id="gov-rock-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#fed7aa" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="#ffedd5" stopOpacity="0.8" />
                </linearGradient>
              </defs>

              {/* Grid Background */}
              <rect x="36" y="6" width="280" height="74" fill="url(#radar-grid)" />
              <line x1="36" y1="6" x2="36" y2="80" stroke="#cbd5e1" strokeWidth="1.2" />
              <line x1="36" y1="80" x2="316" y2="80" stroke="#cbd5e1" strokeWidth="1.2" />

              {/* Y-Axis Reference Guide Lines */}
              <line x1="36" y1="14" x2="316" y2="14" stroke="#cbd5e1" strokeDasharray="3,3" strokeWidth="0.8" />
              <line x1="36" y1="42" x2="316" y2="42" stroke="#cbd5e1" strokeDasharray="3,3" strokeWidth="0.8" />
              <line x1="36" y1="68" x2="316" y2="68" stroke="#cbd5e1" strokeDasharray="3,3" strokeWidth="0.8" />

              {/* Y-Axis Labels (Depth in Metres) */}
              <text x="32" y="17" fill="#475569" fontSize="8" fontWeight="700" fontFamily="Inter" textAnchor="end">0 m</text>
              <text x="32" y="45" fill="#475569" fontSize="8" fontWeight="700" fontFamily="Inter" textAnchor="end">-70 m</text>
              <text x="32" y="71" fill="#ea580c" fontSize="8" fontWeight="800" fontFamily="Inter" textAnchor="end">-142 m</text>

              {/* Layer 1: Top Snow Layer (0 to 15m) */}
              <path
                d="M 36 14 C 95 16, 180 13, 316 15 L 316 23 C 180 21, 95 24, 36 22 Z"
                fill="url(#gov-snow-fill)"
              />
              <path
                d="M 36 14 C 95 16, 180 13, 316 15"
                fill="none"
                stroke="#0284c7"
                strokeWidth="1.8"
              />

              {/* Layer 2: Solid Ice Sheet (15m to 142m) */}
              <path
                d="M 36 22 C 95 24, 180 21, 316 23 L 316 67 C 200 64, 110 70, 36 67 Z"
                fill="url(#gov-ice-fill)"
              />
              <path
                d="M 36 42 C 110 39, 210 45, 316 41"
                fill="none"
                stroke="#0284c7"
                strokeWidth="1"
                strokeDasharray="4,2"
              />

              {/* Layer 3: Solid Mountain Bedrock Floor Line (-142m) */}
              <path
                d="M 36 67 C 110 70, 200 64, 316 67 L 316 80 L 36 80 Z"
                fill="url(#gov-rock-fill)"
              />
              <path
                d="M 36 67 C 110 70, 200 64, 316 67"
                fill="none"
                stroke="#ea580c"
                strokeWidth="2.4"
                strokeLinecap="round"
              />

              {/* X-Axis Distance Labels */}
              <text x="40" y="78" fill="#64748b" fontSize="7" fontWeight="600" fontFamily="Inter">0 m (Base Start)</text>
              <text x="176" y="78" fill="#64748b" fontSize="7" fontWeight="600" fontFamily="Inter" textAnchor="middle">100 m</text>
              <text x="312" y="78" fill="#64748b" fontSize="7" fontWeight="600" fontFamily="Inter" textAnchor="end">200 m (End)</text>
            </svg>

            {/* Official Station Perimeter Watermark */}
            <div
              style={{
                position: 'absolute',
                top: 8,
                right: 10,
                fontSize: 8,
                fontWeight: 700,
                color: '#0b3b60',
                background: 'rgba(255, 255, 255, 0.9)',
                border: '1px solid #cbd5e1',
                padding: '1px 5px',
                borderRadius: 2,
              }}
            >
              GSI RADAR PROFILE LINE 04
            </div>
          </div>

          {/* Simple Government Metrics Bar (Plain, Easy Words) */}
          <div
            style={{
              background: '#ffffff',
              padding: '6px 10px',
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 8,
              textAlign: 'center',
            }}
          >
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '4px 6px', borderRadius: 2 }}>
              <div style={{ fontSize: 8.5, color: '#64748b', fontWeight: 700 }}>ICE THICKNESS</div>
              <div style={{ fontSize: 13, color: '#0b3b60', fontWeight: 800 }}>142.4 Metres</div>
              <div style={{ fontSize: 8, color: '#16a34a', fontWeight: 600 }}>Solid & Stable Ice</div>
            </div>

            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '4px 6px', borderRadius: 2 }}>
              <div style={{ fontSize: 8.5, color: '#64748b', fontWeight: 700 }}>GROUND CRACKS</div>
              <div style={{ fontSize: 13, color: '#16a34a', fontWeight: 800 }}>None (Zero)</div>
              <div style={{ fontSize: 8, color: '#16a34a', fontWeight: 600 }}>100% Safe Ground</div>
            </div>

            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '4px 6px', borderRadius: 2 }}>
              <div style={{ fontSize: 8.5, color: '#64748b', fontWeight: 700 }}>BEDROCK DEPTH</div>
              <div style={{ fontSize: 13, color: '#ea580c', fontWeight: 800 }}>-142.4 Metres</div>
              <div style={{ fontSize: 8, color: '#64748b', fontWeight: 600 }}>Solid Continental Rock</div>
            </div>
          </div>

          {/* Official Verification Footer */}
          <div
            style={{
              background: '#f1f5f9',
              borderTop: '1px solid #e2e8f0',
              padding: '3px 10px',
              fontSize: 8.5,
              color: '#475569',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>● 400 MHz High-Resolution Radar Survey (GSI & NCPOR)</span>
            <span style={{ color: '#15803d', fontWeight: 700 }}>✓ Certified Safe Foundation</span>
          </div>
        </div>
      ) : (
        /* ── LIFE SUPPORT & WATER VIEW ── */
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#ffffff' }}>
          {/* Source Banner */}
          <div
            style={{
              background: '#f0fdf4',
              borderBottom: '1px solid #dcfce7',
              padding: '5px 10px',
              fontSize: 9.5,
              fontWeight: 700,
              color: '#166534',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#16a34a' }}>
                verified
              </span>
              <span>{lssData.source}</span>
            </div>
            <span style={{ fontSize: 8.5, background: '#bbf7d0', padding: '1px 6px', borderRadius: 2, color: '#14532d', fontWeight: 800 }}>
              SAFE TO DRINK
            </span>
          </div>

          {/* Water Storage Bar */}
          <div style={{ padding: '8px 12px 6px 12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
              <span style={{ fontSize: 9.5, fontWeight: 700, color: '#64748b', letterSpacing: '0.03em' }}>
                {t('lss.storage')}
              </span>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#0284c7', fontFamily: 'Inter' }}>
                {lssData.reserveL} ({lssData.percent}% Full) • {lssData.days}
              </span>
            </div>
            <div style={{ width: '100%', height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${lssData.percent}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #0284c7, #38bdf8)',
                  borderRadius: 3,
                }}
              />
            </div>
          </div>

          {/* 3 Simple Telemetry Tiles */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, padding: '0 10px 8px 10px', flex: 1 }}>
            {/* Tile 1: Pipe Freeze Guard */}
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '5px 8px', borderRadius: 2 }}>
              <div style={{ fontSize: 8.5, fontWeight: 700, color: '#64748b' }}>
                {t('lss.heating')}
              </div>
              <div style={{ fontSize: 11, fontWeight: 800, color: '#16a34a', marginTop: 1 }}>
                {lssData.heatState}
              </div>
              <div style={{ fontSize: 8, color: '#64748b' }}>No ice in pipe</div>
            </div>

            {/* Tile 2: Room Temperature */}
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '5px 8px', borderRadius: 2 }}>
              <div style={{ fontSize: 8.5, fontWeight: 700, color: '#64748b' }}>
                {t('lss.indoor_temp')}
              </div>
              <div style={{ fontSize: 11, fontWeight: 800, color: '#0f172a', marginTop: 1 }}>
                {lssData.habitatTemp}
              </div>
              <div style={{ fontSize: 8, color: '#64748b' }}>{lssData.habitatZone}</div>
            </div>

            {/* Tile 3: Fresh Air */}
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '5px 8px', borderRadius: 2 }}>
              <div style={{ fontSize: 8.5, fontWeight: 700, color: '#64748b' }}>
                {t('lss.air_quality')}
              </div>
              <div style={{ fontSize: 11, fontWeight: 800, color: '#0f172a', marginTop: 1 }}>
                {lssData.airO2}
              </div>
              <div style={{ fontSize: 8, color: '#16a34a', fontWeight: 600 }}>{lssData.airSub}</div>
            </div>
          </div>

          {/* Clean Government Verified Footer */}
          <div
            style={{
              background: '#f1f5f9',
              borderTop: '1px solid #e2e8f0',
              padding: '3px 10px',
              fontSize: 8.5,
              color: '#475569',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>● 100% Pure Drinking Water (Govt Tested)</span>
            <span style={{ color: '#0284c7', fontWeight: 700 }}>✓ {lssData.division}</span>
          </div>
        </div>
      )}
    </div>
  )
}
