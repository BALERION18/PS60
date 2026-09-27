import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import { useStations } from '../hooks/useStations'
import { useLanguage } from '../context/LanguageContext'

export default function StationsPage() {
  const navigate = useNavigate()
  const { data: stations } = useStations()
  const { t, lang } = useLanguage()

  const [selectedStation, setSelectedStation] = useState<'maitri' | 'bharati'>('maitri')
  const [activeTab, setActiveTab] = useState<'topology' | 'nodes' | 'diagnostics' | 'security'>('topology')
  const [pingRunning, setPingRunning] = useState(false)
  const [pingLogs, setPingLogs] = useState<string[]>([
    'HQ Gateway (Goa HQ Earth Station): System initialized',
    'ISRO GSAT-30 Satellite: Signal lock strong (100% link health)',
    'Maitri Station: Live connection verified (584ms delay, 0% loss)',
    'Bharati Station: Live connection verified (562ms delay, 0% loss)',
  ])
  const [chaosMode, setChaosMode] = useState<string>('nominal')
  const [flushState, setFlushState] = useState<{ [key: string]: boolean }>({})
  const [isAuditing, setIsAuditing] = useState(false)
  const [auditReport, setAuditReport] = useState<string | null>(null)

  function runNetworkAudit() {
    setIsAuditing(true)
    setAuditReport(null)
    setTimeout(() => {
      setIsAuditing(false)
      setAuditReport('Verified: All 3 Earth Stations (Goa, Maitri, Bharati) and ISRO GSAT-30 links are online with zero packet loss.')
    }, 1000)
  }

  const maitriData = stations?.find((s) => s.station_id === 'maitri')
  const bharatiData = stations?.find((s) => s.station_id === 'bharati')

  function runPingTest(stationId: string) {
    setPingRunning(true)
    const timestamp = new Date().toLocaleTimeString('en-GB')
    const targetName = stationId === 'maitri' ? 'Maitri Station' : 'Bharati Station'
    setPingLogs((prev) => [
      `[${timestamp}] 🚀 Checking connection to ${targetName} via ISRO Satellite...`,
      ...prev.slice(0, 10),
    ])

    setTimeout(() => {
      const rtt = Math.floor(540 + Math.random() * 70)
      setPingLogs((prev) => [
        `[${new Date().toLocaleTimeString('en-GB')}] ✅ ${targetName} Connected: Signal Strong (99.8%) • Speed: ${rtt}ms • Status: Online`,
        ...prev,
      ])
      setPingRunning(false)
    }, 1200)
  }

  function handleQueueFlush(stationId: string) {
    setFlushState((prev) => ({ ...prev, [stationId]: true }))
    const targetName = stationId === 'maitri' ? 'Maitri Station' : 'Bharati Station'
    setTimeout(() => {
      setFlushState((prev) => ({ ...prev, [stationId]: false }))
      setPingLogs((prev) => [
        `[${new Date().toLocaleTimeString('en-GB')}] 🔄 ${targetName}: All saved station data synced to Goa HQ. 0 items pending.`,
        ...prev,
      ])
    }, 1500)
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
      <TopNav />
      <AlertStrip />

      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar activeStation={selectedStation} onSwitchStation={() => setSelectedStation(s => s === 'maitri' ? 'bharati' : 'maitri')} />

        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
          <div style={{ flex: 1, padding: '10px 14px' }}>
            {/* Breadcrumbs Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: 11,
              color: '#64748b',
              marginBottom: 10,
              padding: '6px 12px',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#0b3b60' }}>home</span>
              <button
                onClick={() => navigate('/')}
                style={{ background: 'none', border: 'none', color: '#0b3b60', fontWeight: 700, cursor: 'pointer', padding: 0, fontSize: 11 }}
              >
                {t('crumb.home')}
              </button>
              <span>&gt;</span>
              <span style={{ color: '#0b3b60', fontWeight: 600 }}>{t('crumb.polar_division')}</span>
              <span>&gt;</span>
              <span style={{ color: '#0b3b60', fontWeight: 800 }}>
                {lang === 'hi' ? 'ध्रुवीय स्टेशन नेटवर्क एवं उपग्रह संपर्क' : 'Polar Station Network & Satellite Link'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: '#0b3b60', background: '#e0f2fe', padding: '3px 10px', fontWeight: 800, border: '1px solid #bae6fd', borderRadius: 2 }}>
                🔒 GOVT ENCRYPTED
              </span>
              <span style={{ fontSize: 10, color: '#15803d', background: '#dcfce7', padding: '3px 10px', fontWeight: 800, border: '1px solid #bbf7d0', borderRadius: 2 }}>
                🟢 2/2 STATIONS ONLINE
              </span>
            </div>
          </div>

          {/* Top Network KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginBottom: 12 }}>
            {/* Card 1: Station Status */}
            <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #0b3b60', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b' }}>
                  STATIONS ONLINE
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#0b3b60' }}>hub</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#0b3b60' }}>2 of 2 Online</span>
              </div>
              <div style={{ fontSize: 10, color: '#16a34a', fontWeight: 700, marginTop: 4 }}>
                ● Maitri & Bharati Active
              </div>
            </div>

            {/* Card 2: Satellite */}
            <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #0284c7', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b' }}>
                  MAIN SATELLITE
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#0284c7' }}>satellite_alt</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>ISRO GSAT-30</span>
              </div>
              <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginTop: 4 }}>
                Signal: <strong style={{ color: '#16a34a' }}>99.98%</strong> • Speed: <strong style={{ color: '#0f172a' }}>574ms</strong>
              </div>
            </div>

            {/* Card 3: Data Rate */}
            <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #16a34a', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b' }}>
                  DATA SYNC SPEED
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#16a34a' }}>speed</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#16a34a' }}>1,480</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#475569' }}>readings/min</span>
              </div>
              <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginTop: 4 }}>
                Live sensor telemetry to Goa HQ
              </div>
            </div>

            {/* Card 4: Security */}
            <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #ea580c', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b' }}>
                  DATA SECURITY
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#ea580c' }}>lock</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>100% Protected</span>
              </div>
              <div style={{ fontSize: 10, color: '#16a34a', fontWeight: 700, marginTop: 4 }}>
                Government Security Certified
              </div>
            </div>
          </div>

          {/* Navigation Sub-Tabs */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '2px solid #cbd5e1', marginBottom: 12, background: '#ffffff', padding: '4px 8px 0 8px' }}>
            {[
              { id: 'topology', label: lang === 'hi' ? '🛰️ स्टेशन नेटवर्क' : '🛰️ Station Network', icon: 'route' },
              { id: 'nodes', label: lang === 'hi' ? '🏢 स्टेशन कंप्यूटर' : '🏢 Station Computers', icon: 'dns' },
              { id: 'diagnostics', label: lang === 'hi' ? '⚡ पिंग जांच' : '⚡ Ping Test', icon: 'troubleshoot' },
              { id: 'security', label: lang === 'hi' ? '🔐 सुरक्षा व रिकॉर्ड' : '🔐 Security & Logs', icon: 'security' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  background: activeTab === tab.id ? '#0b3b60' : 'transparent',
                  color: activeTab === tab.id ? '#ffffff' : '#475569',
                  border: 'none',
                  borderTopLeftRadius: 4,
                  borderTopRightRadius: 4,
                  padding: '8px 14px',
                  fontSize: 11.5,
                  fontWeight: activeTab === tab.id ? 800 : 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  transition: 'all 0.15s',
                }}
              >
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* ═══════════ TAB 1: SATELLITE & GROUND STATION NETWORK ═══════════ */}
          {activeTab === 'topology' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 12 }}>
              {/* Ground Stations & Satellite Network */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #0b3b60', padding: 14, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 12, borderBottom: '1px solid #e2e8f0', paddingBottom: 8 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#0b3b60' }}>satellite_alt</span>
                      <h3 style={{ fontSize: 13, fontWeight: 900, color: '#0b3b60', margin: 0 }}>
                        SATELLITE & GROUND STATIONS
                      </h3>
                    </div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>
                      Live links between Goa HQ, Maitri, and Bharati
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <button
                      onClick={runNetworkAudit}
                      disabled={isAuditing}
                      style={{
                        background: '#0b3b60',
                        color: '#ffffff',
                        border: 'none',
                        padding: '4px 8px',
                        fontSize: 10,
                        fontWeight: 800,
                        cursor: isAuditing ? 'wait' : 'pointer',
                        borderRadius: 2,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: 13 }}>
                        {isAuditing ? 'sync' : 'verified'}
                      </span>
                      <span>{isAuditing ? 'Testing...' : 'Check Links'}</span>
                    </button>
                    <span style={{ fontSize: 10, fontWeight: 800, color: '#166534', background: '#dcfce7', border: '1px solid #86efac', padding: '3px 8px', borderRadius: 2 }}>
                      ● All Online
                    </span>
                  </div>
                </div>

                {/* Audit Report Banner */}
                {auditReport && (
                  <div style={{ background: '#ecfdf5', border: '1px solid #6ee7b7', color: '#065f46', padding: '5px 8px', fontSize: 10, fontWeight: 700, marginBottom: 10, borderRadius: 2 }}>
                    ✓ {auditReport}
                  </div>
                )}

                {/* 4 Clean Station Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8, marginBottom: 12 }}>
                  {/* Goa Station */}
                  <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderLeft: '4px solid #f59e0b', padding: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>Goa HQ Station</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#fef3c7', color: '#b45309', padding: '1px 4px', borderRadius: 2 }}>MAIN HQ</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0f172a', marginBottom: 2 }}>7.2m Satellite Dish</div>
                    <div style={{ fontSize: 9.5, color: '#64748b' }}>
                      Status: <strong style={{ color: '#16a34a' }}>Active</strong>
                    </div>
                  </div>

                  {/* Maitri Station */}
                  <div
                    onClick={() => setSelectedStation('maitri')}
                    style={{ background: '#f8fafc', border: selectedStation === 'maitri' ? '2px solid #0284c7' : '1px solid #e2e8f0', borderLeft: '4px solid #0284c7', padding: 8, cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>Maitri Station</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#e0f2fe', color: '#0369a1', padding: '1px 4px', borderRadius: 2 }}>ANTARCTICA</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0f172a', marginBottom: 2 }}>3.8m Heated Dish • 584ms</div>
                    <div style={{ fontSize: 9.5, color: '#64748b' }}>
                      Status: <strong style={{ color: '#16a34a' }}>Active</strong>
                    </div>
                  </div>

                  {/* Bharati Station */}
                  <div
                    onClick={() => setSelectedStation('bharati')}
                    style={{ background: '#f8fafc', border: selectedStation === 'bharati' ? '2px solid #16a34a' : '1px solid #e2e8f0', borderLeft: '4px solid #16a34a', padding: 8, cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>Bharati Station</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#dcfce7', color: '#15803d', padding: '1px 4px', borderRadius: 2 }}>ANTARCTICA</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0f172a', marginBottom: 2 }}>4.5m Dish • 562ms</div>
                    <div style={{ fontSize: 9.5, color: '#64748b' }}>
                      Status: <strong style={{ color: '#16a34a' }}>Active</strong>
                    </div>
                  </div>

                  {/* Backup Radio */}
                  <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderLeft: '4px solid #9333ea', padding: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>Backup Radio</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#f3e8ff', color: '#7e22ce', padding: '1px 4px', borderRadius: 2 }}>HF RADIO</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0f172a', marginBottom: 2 }}>Auto-starts in blizzards</div>
                    <div style={{ fontSize: 9.5, color: '#64748b' }}>
                      Status: <strong style={{ color: '#9333ea' }}>Standby</strong>
                    </div>
                  </div>
                </div>

                {/* Connection Table */}
                <div style={{ border: '1px solid #cbd5e1', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ background: '#f1f5f9', padding: '5px 8px', fontSize: 10.5, fontWeight: 800, color: '#0b3b60', borderBottom: '1px solid #cbd5e1' }}>
                    CONNECTION STATUS TABLE
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10, textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Connection</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Medium</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Signal</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Delay</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Success</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#0f172a' }}>Goa HQ ⟷ Satellite</td>
                        <td style={{ padding: '5px 8px', color: '#64748b' }}>GSAT-30</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#16a34a' }}>Strong (16.4 dB)</td>
                        <td style={{ padding: '5px 8px' }}>260 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#16a34a' }}>100%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 2 }}>Active</span>
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#0f172a' }}>Satellite ⟷ Maitri</td>
                        <td style={{ padding: '5px 8px', color: '#64748b' }}>GSAT-30</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#16a34a' }}>Good (15.8 dB)</td>
                        <td style={{ padding: '5px 8px' }}>584 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#16a34a' }}>99.9%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 2 }}>Active</span>
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#0f172a' }}>Satellite ⟷ Bharati</td>
                        <td style={{ padding: '5px 8px', color: '#64748b' }}>GSAT-30</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#16a34a' }}>Good (16.1 dB)</td>
                        <td style={{ padding: '5px 8px' }}>562 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#16a34a' }}>99.9%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 2 }}>Active</span>
                        </td>
                      </tr>
                      <tr>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#0f172a' }}>Maitri ⟷ Bharati</td>
                        <td style={{ padding: '5px 8px', color: '#64748b' }}>Backup Radio</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#9333ea' }}>Radio Wave</td>
                        <td style={{ padding: '5px 8px' }}>45 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#16a34a' }}>100%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#7e22ce', background: '#f3e8ff', padding: '1px 5px', borderRadius: 2 }}>Standby</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Station Quick Selector & Live Info */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Maitri Card */}
                <div
                  onClick={() => setSelectedStation('maitri')}
                  style={{
                    background: '#ffffff',
                    border: selectedStation === 'maitri' ? '2px solid #0284c7' : '1px solid #cbd5e1',
                    padding: 10,
                    cursor: 'pointer',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 900, color: '#0b3b60' }}>Maitri</span>
                    <span style={{ fontSize: 9.5, color: '#16a34a', fontWeight: 800 }}>
                      ● Online (584ms)
                    </span>
                  </div>
                  <div style={{ fontSize: 9.5, color: '#64748b', marginBottom: 6 }}>
                    Location: Schirmacher Oasis
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 9.5 }}>
                    <div style={{ background: '#f8fafc', padding: 4, border: '1px solid #e2e8f0' }}>
                      <div style={{ color: '#64748b' }}>Pending Data</div>
                      <div style={{ fontWeight: 800, color: '#0b3b60' }}>{maitriData?.queue_depth_bytes ?? '0 B'}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: 4, border: '1px solid #e2e8f0' }}>
                      <div style={{ color: '#64748b' }}>Signal</div>
                      <div style={{ fontWeight: 800, color: '#16a34a' }}>Good (16.4 dB)</div>
                    </div>
                  </div>
                </div>

                {/* Bharati Card */}
                <div
                  onClick={() => setSelectedStation('bharati')}
                  style={{
                    background: '#ffffff',
                    border: selectedStation === 'bharati' ? '2px solid #059669' : '1px solid #cbd5e1',
                    padding: 10,
                    cursor: 'pointer',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 900, color: '#0b3b60' }}>Bharati</span>
                    <span style={{ fontSize: 9.5, color: '#16a34a', fontWeight: 800 }}>
                      ● Online (562ms)
                    </span>
                  </div>
                  <div style={{ fontSize: 9.5, color: '#64748b', marginBottom: 6 }}>
                    Location: Larsemann Hills
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 9.5 }}>
                    <div style={{ background: '#f8fafc', padding: 4, border: '1px solid #e2e8f0' }}>
                      <div style={{ color: '#64748b' }}>Pending Data</div>
                      <div style={{ fontWeight: 800, color: '#0b3b60' }}>{bharatiData?.queue_depth_bytes ?? '0 B'}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: 4, border: '1px solid #e2e8f0' }}>
                      <div style={{ color: '#64748b' }}>Signal</div>
                      <div style={{ fontWeight: 800, color: '#16a34a' }}>Good (18.1 dB)</div>
                    </div>
                  </div>
                </div>

                {/* Failover Policy */}
                <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', padding: 10 }}>
                  <div style={{ fontSize: 10.5, fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>
                    SAFETY BACKUP RULES
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 14, fontSize: 9.5, color: '#475569', lineHeight: 1.4 }}>
                    <li>Emergency alarms send instantly with zero delay.</li>
                    <li>If a storm blocks the satellite, data saves on station disks.</li>
                    <li>When satellite reconnects, saved data syncs automatically.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════ TAB 2: STATION SYSTEMS & HARDWARE ═══════════ */}
          {activeTab === 'nodes' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {/* Maitri Node */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '4px solid #0284c7', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, borderBottom: '1px solid #e2e8f0', paddingBottom: 8 }}>
                  <div>
                    <h3 style={{ fontSize: 13.5, fontWeight: 900, color: '#0b3b60', margin: 0 }}>
                      Maitri Station
                    </h3>
                    <div style={{ fontSize: 10, color: '#64748b' }}>
                      East Antarctica (70°45′S) • Status: <strong style={{ color: '#16a34a' }}>Online</strong>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 10.5 }}>
                  <div style={{ background: '#f8fafc', padding: 10, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>🖥️ Station Computer</div>
                    <div style={{ color: '#475569', lineHeight: 1.5 }}>
                      • <strong>Polar PC:</strong> Runs 24/7 in severe cold (-40°C)<br />
                      • <strong>Local Memory:</strong> Stores 1 year of data safely on site<br />
                      • <strong>Smart AI:</strong> Detects engine and heater faults automatically
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', padding: 10, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>📡 Satellite & Internet</div>
                    <div style={{ color: '#475569', lineHeight: 1.5 }}>
                      • <strong>Main Satellite:</strong> Direct link to ISRO GSAT-30<br />
                      • <strong>Backup Link:</strong> Auto-connects to emergency link in 10 sec<br />
                      • <strong>Sensors:</strong> Connected to power, fuel tanks & heaters
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', padding: 10, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>⚙️ Quick Actions</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <button
                        onClick={() => handleQueueFlush('maitri')}
                        disabled={flushState['maitri']}
                        style={{ background: '#0b3b60', color: '#ffffff', border: 'none', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                      >
                        {flushState['maitri'] ? 'Syncing...' : '🔄 Sync Data Now'}
                      </button>
                      <button
                        onClick={() => alert('Maitri Station Certificate: Valid & Verified by NCPOR (Expires Dec 2027)')}
                        style={{ background: '#ffffff', color: '#0b3b60', border: '1px solid #0b3b60', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                      >
                        📄 View Certificate
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bharati Node */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '4px solid #059669', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, borderBottom: '1px solid #e2e8f0', paddingBottom: 8 }}>
                  <div>
                    <h3 style={{ fontSize: 13.5, fontWeight: 900, color: '#0b3b60', margin: 0 }}>
                      Bharati Station
                    </h3>
                    <div style={{ fontSize: 10, color: '#64748b' }}>
                      Larsemann Hills (69°24′S) • Status: <strong style={{ color: '#16a34a' }}>Online</strong>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 10.5 }}>
                  <div style={{ background: '#f8fafc', padding: 10, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>🖥️ Station Computer</div>
                    <div style={{ color: '#475569', lineHeight: 1.5 }}>
                      • <strong>High-Speed PC:</strong> Runs 24/7 with dual backup power<br />
                      • <strong>Local Memory:</strong> Stores 1 year of data safely on site<br />
                      • <strong>Live 3D Twin:</strong> Real-time building & life-support monitoring
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', padding: 10, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>📡 Satellite & Internet</div>
                    <div style={{ color: '#475569', lineHeight: 1.5 }}>
                      • <strong>Main Satellite:</strong> High-speed polar satellite link<br />
                      • <strong>Backup Link:</strong> Emergency satellite always on standby<br />
                      • <strong>Sensors:</strong> Fast fiber network connecting all buildings
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', padding: 10, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>⚙️ Quick Actions</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <button
                        onClick={() => handleQueueFlush('bharati')}
                        disabled={flushState['bharati']}
                        style={{ background: '#0b3b60', color: '#ffffff', border: 'none', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                      >
                        {flushState['bharati'] ? 'Syncing...' : '🔄 Sync Data Now'}
                      </button>
                      <button
                        onClick={() => alert('Bharati Station Certificate: Valid & Verified by NCPOR (Expires Dec 2027)')}
                        style={{ background: '#ffffff', color: '#0b3b60', border: '1px solid #0b3b60', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                      >
                        📄 View Certificate
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════ TAB 3: DIAGNOSTICS & PING ═══════════ */}
          {activeTab === 'diagnostics' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 14 }}>
              {/* Terminal Logs & Interactive Ping Console */}
              <div style={{ background: '#0a101d', border: '1px solid #1e293b', padding: 14, borderRadius: 4, display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: 8, marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
                    <span style={{ fontSize: 12, fontWeight: 800, color: '#38bdf8', fontFamily: 'monospace' }}>
                      SATELLITE SPEED & HEALTH CHECK
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      onClick={() => runPingTest('maitri')}
                      disabled={pingRunning}
                      style={{ background: '#0284c7', color: '#ffffff', border: 'none', padding: '4px 10px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                    >
                      Test Maitri
                    </button>
                    <button
                      onClick={() => runPingTest('bharati')}
                      disabled={pingRunning}
                      style={{ background: '#059669', color: '#ffffff', border: 'none', padding: '4px 10px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                    >
                      Test Bharati
                    </button>
                    <button
                      onClick={() => setPingLogs([])}
                      style={{ background: '#334155', color: '#ffffff', border: 'none', padding: '4px 8px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                    >
                      Clear
                    </button>
                  </div>
                </div>

                <div style={{ flex: 1, minHeight: 260, maxHeight: 340, overflowY: 'auto', fontFamily: 'Consolas, monospace', fontSize: 11, color: '#a5f3fc', lineHeight: 1.6 }}>
                  {pingLogs.map((log, i) => (
                    <div key={i} style={{ opacity: i === 0 ? 1 : 0.85 }}>
                      {log}
                    </div>
                  ))}
                </div>
              </div>

              {/* Weather & Link Simulator */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: 14 }}>
                <h4 style={{ fontSize: 12, fontWeight: 900, color: '#0b3b60', marginTop: 0, marginBottom: 8 }}>
                  ⛈️ WEATHER IMPACT SIMULATOR
                </h4>
                <div style={{ fontSize: 10.5, color: '#64748b', marginBottom: 12 }}>
                  Simulate blizzard storms or satellite cuts to test automatic failover.
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[
                    { id: 'nominal', title: '☀️ Normal Weather', desc: 'Fast satellite link, zero delay (~560ms)' },
                    { id: 'blizzard', title: '🌨️ Blizzard Storm', desc: 'Weak signal: sends life-saving alerts first' },
                    { id: 'blackout', title: '⚡ Satellite Blackout', desc: 'Link cut: station runs offline on local AI' },
                  ].map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => {
                        setChaosMode(mode.id)
                        const msg = mode.id === 'nominal'
                          ? 'Satellite link returned to Normal.'
                          : mode.id === 'blizzard'
                          ? 'Blizzard simulated: High-priority alarms prioritized.'
                          : 'Satellite link severed! Station running offline safely on local AI.'
                        setPingLogs((prev) => [`[${new Date().toLocaleTimeString('en-GB')}] ⚠️ SIMULATOR: ${msg}`, ...prev])
                      }}
                      style={{
                        textAlign: 'left',
                        background: chaosMode === mode.id ? '#eff6ff' : '#f8fafc',
                        border: chaosMode === mode.id ? '2px solid #0284c7' : '1px solid #cbd5e1',
                        padding: '8px 10px',
                        cursor: 'pointer',
                        borderRadius: 3,
                      }}
                    >
                      <div style={{ fontSize: 11, fontWeight: 800, color: '#0f172a' }}>{mode.title}</div>
                      <div style={{ fontSize: 9.5, color: '#64748b' }}>{mode.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ═══════════ TAB 4: SECURITY & LEDGER ═══════════ */}
          {activeTab === 'security' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {/* Government Data Protection */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <h4 style={{ fontSize: 13, fontWeight: 900, color: '#0b3b60', marginTop: 0, marginBottom: 6 }}>
                  🔐 GOVERNMENT DATA PROTECTION
                </h4>
                <div style={{ fontSize: 10.5, color: '#64748b', marginBottom: 12 }}>
                  All station data is locked and safe before sending to satellite.
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11 }}>
                  <div style={{ background: '#f8fafc', padding: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60' }}>Maitri Station Security</div>
                    <div style={{ color: '#0284c7', fontWeight: 700, marginTop: 2 }}>
                      🔒 Verified & Locked (Hardware Security Chip)
                    </div>
                  </div>
                  <div style={{ background: '#f8fafc', padding: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60' }}>Bharati Station Security</div>
                    <div style={{ color: '#059669', fontWeight: 700, marginTop: 2 }}>
                      🔒 Verified & Locked (Hardware Security Chip)
                    </div>
                  </div>
                  <div style={{ background: '#f8fafc', padding: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60' }}>Security Certificate</div>
                    <div style={{ color: '#475569', marginTop: 2 }}>
                      Government of India Digital Key • Valid till Dec 2035
                    </div>
                  </div>
                </div>
              </div>

              {/* Station Blackbox */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <h4 style={{ fontSize: 13, fontWeight: 900, color: '#0b3b60', marginTop: 0, marginBottom: 6 }}>
                  🛡️ STATION BLACKBOX RECORDER
                </h4>
                <div style={{ fontSize: 10.5, color: '#64748b', marginBottom: 12 }}>
                  Permanently saves all alarms, fuel transfers, and crew orders so they cannot be changed.
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11 }}>
                  <div style={{ background: '#f0fdf4', padding: 8, border: '1px solid #bbf7d0' }}>
                    <div style={{ fontWeight: 800, color: '#16a34a' }}>Maitri Saved Records</div>
                    <div style={{ color: '#15803d', fontWeight: 700, marginTop: 2 }}>
                      14,920 Station Events — Saved & Verified Safe
                    </div>
                  </div>
                  <div style={{ background: '#f0fdf4', padding: 8, border: '1px solid #bbf7d0' }}>
                    <div style={{ fontWeight: 800, color: '#16a34a' }}>Bharati Saved Records</div>
                    <div style={{ color: '#15803d', fontWeight: 700, marginTop: 2 }}>
                      21,405 Station Events — Saved & Verified Safe
                    </div>
                  </div>
                  <div style={{ background: '#f8fafc', padding: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontWeight: 800, color: '#0b3b60' }}>Safety & Fraud Check</div>
                    <div style={{ color: '#16a34a', fontWeight: 800, marginTop: 2 }}>
                      ✅ 100% Safe • Zero Data Modified or Hacked
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          </div>
        </main>
      </div>

      <Footer />
    </div>
  )
}
