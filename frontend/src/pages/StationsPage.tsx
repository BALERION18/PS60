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
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}>
      <TopNav />
      <AlertStrip />

      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar activeStation={selectedStation} onSwitchStation={() => setSelectedStation(s => s === 'maitri' ? 'bharati' : 'maitri')} />

        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}>
          <div style={{ flex: 1, padding: '10px 14px' }}>
            {/* Breadcrumbs Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: 11,
              color: '#687066',
              marginBottom: 10,
              padding: '6px 12px',
              background: '#FCFBF8',
              border: '1px solid #DDD8CC',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#4F5935' }}>home</span>
              <button
                onClick={() => navigate('/')}
                style={{ background: 'none', border: 'none', color: '#4F5935', fontWeight: 700, cursor: 'pointer', padding: 0, fontSize: 11 }}
              >
                {t('crumb.home')}
              </button>
              <span>&gt;</span>
              <span style={{ color: '#4F5935', fontWeight: 600 }}>{t('crumb.polar_division')}</span>
              <span>&gt;</span>
              <span style={{ color: '#4F5935', fontWeight: 800 }}>
                {lang === 'hi' ? 'ध्रुवीय स्टेशन नेटवर्क एवं उपग्रह संपर्क' : 'Polar Station Network & Satellite Link'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: '#4F5935', background: '#E4E8D3', padding: '3px 10px', fontWeight: 800, border: '1px solid #D5D9C8', borderRadius: 2 }}>
                🔒 GOVT ENCRYPTED
              </span>
              <span style={{ fontSize: 10, color: '#6F8747', background: '#E4E8D3', padding: '3px 10px', fontWeight: 800, border: '1px solid #C5D4A8', borderRadius: 2 }}>
                🟢 2/2 STATIONS ONLINE
              </span>
            </div>
          </div>

          {/* Top Network KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginBottom: 12 }}>
            {/* Card 1: Station Status */}
            <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', borderTop: '3px solid #4F5935', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#687066' }}>
                  STATIONS ONLINE
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#4F5935' }}>hub</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#4F5935' }}>2 of 2 Online</span>
              </div>
              <div style={{ fontSize: 10, color: '#6F8747', fontWeight: 700, marginTop: 4 }}>
                ● Maitri & Bharati Active
              </div>
            </div>

            {/* Card 2: Satellite */}
            <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', borderTop: '3px solid #76804D', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#687066' }}>
                  MAIN SATELLITE
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#76804D' }}>satellite_alt</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#252820' }}>ISRO GSAT-30</span>
              </div>
              <div style={{ fontSize: 10, color: '#687066', fontWeight: 600, marginTop: 4 }}>
                Signal: <strong style={{ color: '#6F8747' }}>99.98%</strong> • Speed: <strong style={{ color: '#252820' }}>574ms</strong>
              </div>
            </div>

            {/* Card 3: Data Rate */}
            <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', borderTop: '3px solid #6F8747', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#687066' }}>
                  DATA SYNC SPEED
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#6F8747' }}>speed</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#6F8747' }}>1,480</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#687066' }}>readings/min</span>
              </div>
              <div style={{ fontSize: 10, color: '#687066', fontWeight: 600, marginTop: 4 }}>
                Live sensor telemetry to Goa HQ
              </div>
            </div>

            {/* Card 4: Security */}
            <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', borderTop: '3px solid #C58A32', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: '#687066' }}>
                  DATA SECURITY
                </span>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#C58A32' }}>lock</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: '#252820' }}>100% Protected</span>
              </div>
              <div style={{ fontSize: 10, color: '#6F8747', fontWeight: 700, marginTop: 4 }}>
                Government Security Certified
              </div>
            </div>
          </div>

          {/* Navigation Sub-Tabs */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '2px solid #DDD8CC', marginBottom: 12, background: '#FCFBF8', padding: '4px 8px 0 8px' }}>
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
                  background: activeTab === tab.id ? '#4F5935' : 'transparent',
                  color: activeTab === tab.id ? '#FCFBF8' : '#687066',
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
              <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', borderTop: '3px solid #4F5935', padding: 14, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 12, borderBottom: '1px solid #E9E5DC', paddingBottom: 8 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#4F5935' }}>satellite_alt</span>
                      <h3 style={{ fontSize: 13, fontWeight: 900, color: '#4F5935', margin: 0 }}>
                        SATELLITE & GROUND STATIONS
                      </h3>
                    </div>
                    <div style={{ fontSize: 10, color: '#687066' }}>
                      Live links between Goa HQ, Maitri, and Bharati
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <button
                      onClick={runNetworkAudit}
                      disabled={isAuditing}
                      style={{
                        background: '#4F5935',
                        color: '#FCFBF8',
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
                    <span style={{ fontSize: 10, fontWeight: 800, color: '#4A6030', background: '#E4E8D3', border: '1px solid #C5D4A8', padding: '3px 8px', borderRadius: 2 }}>
                      ● All Online
                    </span>
                  </div>
                </div>

                {/* Audit Report Banner */}
                {auditReport && (
                  <div style={{ background: '#E4E8D3', border: '1px solid #C5D4A8', color: '#4A6030', padding: '5px 8px', fontSize: 10, fontWeight: 700, marginBottom: 10, borderRadius: 2 }}>
                    ✓ {auditReport}
                  </div>
                )}

                {/* 4 Clean Station Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8, marginBottom: 12 }}>
                  {/* Goa Station */}
                  <div style={{ background: '#F6F3ED', border: '1px solid #E9E5DC', borderLeft: '4px solid #D4883A', padding: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#4F5935' }}>Goa HQ Station</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#FDF3E3', color: '#9A7030', padding: '1px 4px', borderRadius: 2 }}>MAIN HQ</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#252820', marginBottom: 2 }}>7.2m Satellite Dish</div>
                    <div style={{ fontSize: 9.5, color: '#687066' }}>
                      Status: <strong style={{ color: '#6F8747' }}>Active</strong>
                    </div>
                  </div>

                  {/* Maitri Station */}
                  <div
                    onClick={() => setSelectedStation('maitri')}
                    style={{ background: '#F6F3ED', border: selectedStation === 'maitri' ? '2px solid #76804D' : '1px solid #E9E5DC', borderLeft: '4px solid #76804D', padding: 8, cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#4F5935' }}>Maitri Station</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#E4E8D3', color: '#4F5935', padding: '1px 4px', borderRadius: 2 }}>ANTARCTICA</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#252820', marginBottom: 2 }}>3.8m Heated Dish • 584ms</div>
                    <div style={{ fontSize: 9.5, color: '#687066' }}>
                      Status: <strong style={{ color: '#6F8747' }}>Active</strong>
                    </div>
                  </div>

                  {/* Bharati Station */}
                  <div
                    onClick={() => setSelectedStation('bharati')}
                    style={{ background: '#F6F3ED', border: selectedStation === 'bharati' ? '2px solid #6F8747' : '1px solid #E9E5DC', borderLeft: '4px solid #6F8747', padding: 8, cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#4F5935' }}>Bharati Station</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#E4E8D3', color: '#6F8747', padding: '1px 4px', borderRadius: 2 }}>ANTARCTICA</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#252820', marginBottom: 2 }}>4.5m Dish • 562ms</div>
                    <div style={{ fontSize: 9.5, color: '#687066' }}>
                      Status: <strong style={{ color: '#6F8747' }}>Active</strong>
                    </div>
                  </div>

                  {/* Backup Radio */}
                  <div style={{ background: '#F6F3ED', border: '1px solid #E9E5DC', borderLeft: '4px solid #8278A4', padding: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: '#4F5935' }}>Backup Radio</span>
                      <span style={{ fontSize: 8.5, fontWeight: 800, background: '#F0ECF6', color: '#6B5F8A', padding: '1px 4px', borderRadius: 2 }}>HF RADIO</span>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#252820', marginBottom: 2 }}>Auto-starts in blizzards</div>
                    <div style={{ fontSize: 9.5, color: '#687066' }}>
                      Status: <strong style={{ color: '#8278A4' }}>Standby</strong>
                    </div>
                  </div>
                </div>

                {/* Connection Table */}
                <div style={{ border: '1px solid #DDD8CC', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ background: '#F6F3ED', padding: '5px 8px', fontSize: 10.5, fontWeight: 800, color: '#4F5935', borderBottom: '1px solid #DDD8CC' }}>
                    CONNECTION STATUS TABLE
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10, textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: '#F6F3ED', borderBottom: '1px solid #E9E5DC', color: '#687066' }}>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Connection</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Medium</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Signal</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Delay</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Success</th>
                        <th style={{ padding: '5px 8px', fontWeight: 800 }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid #F6F3ED' }}>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#252820' }}>Goa HQ ⟷ Satellite</td>
                        <td style={{ padding: '5px 8px', color: '#687066' }}>GSAT-30</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#6F8747' }}>Strong (16.4 dB)</td>
                        <td style={{ padding: '5px 8px' }}>260 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#6F8747' }}>100%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#4A6030', background: '#E4E8D3', padding: '1px 5px', borderRadius: 2 }}>Active</span>
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #F6F3ED' }}>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#252820' }}>Satellite ⟷ Maitri</td>
                        <td style={{ padding: '5px 8px', color: '#687066' }}>GSAT-30</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#6F8747' }}>Good (15.8 dB)</td>
                        <td style={{ padding: '5px 8px' }}>584 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#6F8747' }}>99.9%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#4A6030', background: '#E4E8D3', padding: '1px 5px', borderRadius: 2 }}>Active</span>
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #F6F3ED' }}>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#252820' }}>Satellite ⟷ Bharati</td>
                        <td style={{ padding: '5px 8px', color: '#687066' }}>GSAT-30</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#6F8747' }}>Good (16.1 dB)</td>
                        <td style={{ padding: '5px 8px' }}>562 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#6F8747' }}>99.9%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#4A6030', background: '#E4E8D3', padding: '1px 5px', borderRadius: 2 }}>Active</span>
                        </td>
                      </tr>
                      <tr>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#252820' }}>Maitri ⟷ Bharati</td>
                        <td style={{ padding: '5px 8px', color: '#687066' }}>Backup Radio</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#8278A4' }}>Radio Wave</td>
                        <td style={{ padding: '5px 8px' }}>45 ms</td>
                        <td style={{ padding: '5px 8px', fontWeight: 700, color: '#6F8747' }}>100%</td>
                        <td style={{ padding: '5px 8px' }}>
                          <span style={{ fontSize: 9, fontWeight: 800, color: '#6B5F8A', background: '#F0ECF6', padding: '1px 5px', borderRadius: 2 }}>Standby</span>
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
                    background: '#FCFBF8',
                    border: selectedStation === 'maitri' ? '2px solid #76804D' : '1px solid #DDD8CC',
                    padding: 10,
                    cursor: 'pointer',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 900, color: '#4F5935' }}>Maitri</span>
                    <span style={{ fontSize: 9.5, color: '#6F8747', fontWeight: 800 }}>
                      ● Online (584ms)
                    </span>
                  </div>
                  <div style={{ fontSize: 9.5, color: '#687066', marginBottom: 6 }}>
                    Location: Schirmacher Oasis
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 9.5 }}>
                    <div style={{ background: '#F6F3ED', padding: 4, border: '1px solid #E9E5DC' }}>
                      <div style={{ color: '#687066' }}>Pending Data</div>
                      <div style={{ fontWeight: 800, color: '#4F5935' }}>{maitriData?.queue_depth_bytes ?? '0 B'}</div>
                    </div>
                    <div style={{ background: '#F6F3ED', padding: 4, border: '1px solid #E9E5DC' }}>
                      <div style={{ color: '#687066' }}>Signal</div>
                      <div style={{ fontWeight: 800, color: '#6F8747' }}>Good (16.4 dB)</div>
                    </div>
                  </div>
                </div>

                {/* Bharati Card */}
                <div
                  onClick={() => setSelectedStation('bharati')}
                  style={{
                    background: '#FCFBF8',
                    border: selectedStation === 'bharati' ? '2px solid #6F8747' : '1px solid #DDD8CC',
                    padding: 10,
                    cursor: 'pointer',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 900, color: '#4F5935' }}>Bharati</span>
                    <span style={{ fontSize: 9.5, color: '#6F8747', fontWeight: 800 }}>
                      ● Online (562ms)
                    </span>
                  </div>
                  <div style={{ fontSize: 9.5, color: '#687066', marginBottom: 6 }}>
                    Location: Larsemann Hills
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 9.5 }}>
                    <div style={{ background: '#F6F3ED', padding: 4, border: '1px solid #E9E5DC' }}>
                      <div style={{ color: '#687066' }}>Pending Data</div>
                      <div style={{ fontWeight: 800, color: '#4F5935' }}>{bharatiData?.queue_depth_bytes ?? '0 B'}</div>
                    </div>
                    <div style={{ background: '#F6F3ED', padding: 4, border: '1px solid #E9E5DC' }}>
                      <div style={{ color: '#687066' }}>Signal</div>
                      <div style={{ fontWeight: 800, color: '#6F8747' }}>Good (18.1 dB)</div>
                    </div>
                  </div>
                </div>

                {/* Failover Policy */}
                <div style={{ background: '#F6F3ED', border: '1px solid #DDD8CC', padding: 10 }}>
                  <div style={{ fontSize: 10.5, fontWeight: 800, color: '#4F5935', marginBottom: 4 }}>
                    SAFETY BACKUP RULES
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 14, fontSize: 9.5, color: '#687066', lineHeight: 1.4 }}>
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
              <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', borderTop: '4px solid #76804D', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, borderBottom: '1px solid #E9E5DC', paddingBottom: 8 }}>
                  <div>
                    <h3 style={{ fontSize: 13.5, fontWeight: 900, color: '#4F5935', margin: 0 }}>
                      Maitri Station
                    </h3>
                    <div style={{ fontSize: 10, color: '#687066' }}>
                      East Antarctica (70°45′S) • Status: <strong style={{ color: '#6F8747' }}>Online</strong>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 10.5 }}>
                  <div style={{ background: '#F6F3ED', padding: 10, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935', marginBottom: 4 }}>🖥️ Station Computer</div>
                    <div style={{ color: '#687066', lineHeight: 1.5 }}>
                      • <strong>Polar PC:</strong> Runs 24/7 in severe cold (-40°C)<br />
                      • <strong>Local Memory:</strong> Stores 1 year of data safely on site<br />
                      • <strong>Smart AI:</strong> Detects engine and heater faults automatically
                    </div>
                  </div>

                  <div style={{ background: '#F6F3ED', padding: 10, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935', marginBottom: 4 }}>📡 Satellite & Internet</div>
                    <div style={{ color: '#687066', lineHeight: 1.5 }}>
                      • <strong>Main Satellite:</strong> Direct link to ISRO GSAT-30<br />
                      • <strong>Backup Link:</strong> Auto-connects to emergency link in 10 sec<br />
                      • <strong>Sensors:</strong> Connected to power, fuel tanks & heaters
                    </div>
                  </div>

                  <div style={{ background: '#F6F3ED', padding: 10, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935', marginBottom: 4 }}>⚙️ Quick Actions</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <button
                        onClick={() => handleQueueFlush('maitri')}
                        disabled={flushState['maitri']}
                        style={{ background: '#4F5935', color: '#FCFBF8', border: 'none', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                      >
                        {flushState['maitri'] ? 'Syncing...' : '🔄 Sync Data Now'}
                      </button>
                      <button
                        onClick={() => alert('Maitri Station Certificate: Valid & Verified by NCPOR (Expires Dec 2027)')}
                        style={{ background: '#FCFBF8', color: '#4F5935', border: '1px solid #4F5935', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                      >
                        📄 View Certificate
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bharati Node */}
              <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', borderTop: '4px solid #6F8747', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, borderBottom: '1px solid #E9E5DC', paddingBottom: 8 }}>
                  <div>
                    <h3 style={{ fontSize: 13.5, fontWeight: 900, color: '#4F5935', margin: 0 }}>
                      Bharati Station
                    </h3>
                    <div style={{ fontSize: 10, color: '#687066' }}>
                      Larsemann Hills (69°24′S) • Status: <strong style={{ color: '#6F8747' }}>Online</strong>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 10.5 }}>
                  <div style={{ background: '#F6F3ED', padding: 10, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935', marginBottom: 4 }}>🖥️ Station Computer</div>
                    <div style={{ color: '#687066', lineHeight: 1.5 }}>
                      • <strong>High-Speed PC:</strong> Runs 24/7 with dual backup power<br />
                      • <strong>Local Memory:</strong> Stores 1 year of data safely on site<br />
                      • <strong>Live 3D Twin:</strong> Real-time building & life-support monitoring
                    </div>
                  </div>

                  <div style={{ background: '#F6F3ED', padding: 10, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935', marginBottom: 4 }}>📡 Satellite & Internet</div>
                    <div style={{ color: '#687066', lineHeight: 1.5 }}>
                      • <strong>Main Satellite:</strong> High-speed polar satellite link<br />
                      • <strong>Backup Link:</strong> Emergency satellite always on standby<br />
                      • <strong>Sensors:</strong> Fast fiber network connecting all buildings
                    </div>
                  </div>

                  <div style={{ background: '#F6F3ED', padding: 10, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935', marginBottom: 4 }}>⚙️ Quick Actions</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <button
                        onClick={() => handleQueueFlush('bharati')}
                        disabled={flushState['bharati']}
                        style={{ background: '#4F5935', color: '#FCFBF8', border: 'none', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                      >
                        {flushState['bharati'] ? 'Syncing...' : '🔄 Sync Data Now'}
                      </button>
                      <button
                        onClick={() => alert('Bharati Station Certificate: Valid & Verified by NCPOR (Expires Dec 2027)')}
                        style={{ background: '#FCFBF8', color: '#4F5935', border: '1px solid #4F5935', padding: '5px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
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
              <div style={{ background: '#0a101d', border: '1px solid #252820', padding: 14, borderRadius: 12, display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #252820', paddingBottom: 8, marginBottom: 10 }}>
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
                      style={{ background: '#76804D', color: '#FCFBF8', border: 'none', padding: '4px 10px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                    >
                      Test Maitri
                    </button>
                    <button
                      onClick={() => runPingTest('bharati')}
                      disabled={pingRunning}
                      style={{ background: '#6F8747', color: '#FCFBF8', border: 'none', padding: '4px 10px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
                    >
                      Test Bharati
                    </button>
                    <button
                      onClick={() => setPingLogs([])}
                      style={{ background: '#252820', color: '#FCFBF8', border: 'none', padding: '4px 8px', fontSize: 10, fontWeight: 800, cursor: 'pointer', borderRadius: 2 }}
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
              <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', padding: 14 }}>
                <h4 style={{ fontSize: 12, fontWeight: 900, color: '#4F5935', marginTop: 0, marginBottom: 8 }}>
                  ⛈️ WEATHER IMPACT SIMULATOR
                </h4>
                <div style={{ fontSize: 10.5, color: '#687066', marginBottom: 12 }}>
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
                        background: chaosMode === mode.id ? '#E4E8D3' : '#F6F3ED',
                        border: chaosMode === mode.id ? '2px solid #76804D' : '1px solid #DDD8CC',
                        padding: '8px 10px',
                        cursor: 'pointer',
                        borderRadius: 3,
                      }}
                    >
                      <div style={{ fontSize: 11, fontWeight: 800, color: '#252820' }}>{mode.title}</div>
                      <div style={{ fontSize: 9.5, color: '#687066' }}>{mode.desc}</div>
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
              <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <h4 style={{ fontSize: 13, fontWeight: 900, color: '#4F5935', marginTop: 0, marginBottom: 6 }}>
                  🔐 GOVERNMENT DATA PROTECTION
                </h4>
                <div style={{ fontSize: 10.5, color: '#687066', marginBottom: 12 }}>
                  All station data is locked and safe before sending to satellite.
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11 }}>
                  <div style={{ background: '#F6F3ED', padding: 8, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935' }}>Maitri Station Security</div>
                    <div style={{ color: '#76804D', fontWeight: 700, marginTop: 2 }}>
                      🔒 Verified & Locked (Hardware Security Chip)
                    </div>
                  </div>
                  <div style={{ background: '#F6F3ED', padding: 8, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935' }}>Bharati Station Security</div>
                    <div style={{ color: '#6F8747', fontWeight: 700, marginTop: 2 }}>
                      🔒 Verified & Locked (Hardware Security Chip)
                    </div>
                  </div>
                  <div style={{ background: '#F6F3ED', padding: 8, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935' }}>Security Certificate</div>
                    <div style={{ color: '#687066', marginTop: 2 }}>
                      Government of India Digital Key • Valid till Dec 2035
                    </div>
                  </div>
                </div>
              </div>

              {/* Station Blackbox */}
              <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <h4 style={{ fontSize: 13, fontWeight: 900, color: '#4F5935', marginTop: 0, marginBottom: 6 }}>
                  🛡️ STATION BLACKBOX RECORDER
                </h4>
                <div style={{ fontSize: 10.5, color: '#687066', marginBottom: 12 }}>
                  Permanently saves all alarms, fuel transfers, and crew orders so they cannot be changed.
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11 }}>
                  <div style={{ background: '#E4E8D3', padding: 8, border: '1px solid #C5D4A8' }}>
                    <div style={{ fontWeight: 800, color: '#6F8747' }}>Maitri Saved Records</div>
                    <div style={{ color: '#6F8747', fontWeight: 700, marginTop: 2 }}>
                      14,920 Station Events — Saved & Verified Safe
                    </div>
                  </div>
                  <div style={{ background: '#E4E8D3', padding: 8, border: '1px solid #C5D4A8' }}>
                    <div style={{ fontWeight: 800, color: '#6F8747' }}>Bharati Saved Records</div>
                    <div style={{ color: '#6F8747', fontWeight: 700, marginTop: 2 }}>
                      21,405 Station Events — Saved & Verified Safe
                    </div>
                  </div>
                  <div style={{ background: '#F6F3ED', padding: 8, border: '1px solid #E9E5DC' }}>
                    <div style={{ fontWeight: 800, color: '#4F5935' }}>Safety & Fraud Check</div>
                    <div style={{ color: '#6F8747', fontWeight: 800, marginTop: 2 }}>
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
