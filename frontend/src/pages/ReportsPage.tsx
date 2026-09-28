import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import { useReport } from '../hooks/useReport'
import { downloadReportFile } from '../api/hq'

type ReportType = 'daily' | 'monthly' | 'incident' | 'scientific' | 'audit'

// ── Types matching backend response ────────────────────────────────────────
interface AlertRow {
  alert_id: string
  severity: string
  domain: string
  description: string
  triggered_at: string
  ack_state: string
}
interface SensorRow {
  sensor_id: string
  domain: string
  value: number
  unit: string
  ts: string
}
interface InventoryRow {
  name: string
  category: string
  quantity: number
  unit: string
  days_remaining: number | null
  status: string
}
interface AssetRow {
  name: string
  asset_type: string
  status: string
}
interface StationInfo {
  display_name: string
  link_state: string
  open_critical_alerts: number
  open_high_alerts: number
  services_healthy: boolean | null
}

// ── Helper colours ──────────────────────────────────────────────────────────
function sevColor(sev: string) {
  if (sev === 'CRITICAL') return '#B85A5A'
  if (sev === 'HIGH') return '#C58A32'
  if (sev === 'MEDIUM') return '#4F5935'
  return '#6F8747'
}
function statusColor(s: string) {
  if (s === 'NOMINAL' || s === 'ACTIVE') return '#6F8747'
  if (s === 'WARNING' || s === 'UNDER_MAINTENANCE') return '#C58A32'
  return '#B85A5A'
}

export default function ReportsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ReportType>('daily')
  const [selectedStation, setSelectedStation] = useState<string>('both')
  const [downloadMsg, setDownloadMsg] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  const stationId = selectedStation === 'both' ? undefined : selectedStation

  // ── Live DB data via backend ────────────────────────────────────────────
  const { data: reportData, isLoading, error } = useReport(activeTab, stationId)

  const tabs: { id: ReportType; label: string; icon: string }[] = [
    { id: 'daily',      label: 'Daily Ops',           icon: 'today' },
    { id: 'monthly',    label: 'Monthly Summary',      icon: 'calendar_month' },
    { id: 'incident',   label: 'Incident / Alerts',    icon: 'report' },
    { id: 'scientific', label: 'Scientific / Sensors', icon: 'science' },
    { id: 'audit',      label: 'Audit / Inventory',    icon: 'fact_check' },
  ]

  // Convenience accessors into the report JSON
  const alertSummary = reportData?.alert_summary as {
    counts_by_severity: Record<string, number>
    total_last_30d: number
    recent: AlertRow[]
  } | undefined

  const stationsInfo = reportData?.stations as Record<string, StationInfo> | undefined
  const sensorSummary = reportData?.sensor_summary as Record<string, { readings_24h: number; latest: SensorRow[] }> | undefined
  const inventory = reportData?.inventory as Record<string, InventoryRow[]> | undefined
  const assets = reportData?.assets as Record<string, AssetRow[]> | undefined
  const stationIds = (reportData?.station_ids as string[] | undefined) ?? []

  async function handleDownload() {
    setIsDownloading(true)
    try {
      const result = await downloadReportFile(activeTab, stationId)
      // Trigger browser file download
      const blob = new Blob([result.content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setDownloadMsg(`✅ Downloaded: ${result.filename}`)
      setTimeout(() => setDownloadMsg(null), 5000)
    } catch {
      setDownloadMsg('❌ Download failed — please try again')
      setTimeout(() => setDownloadMsg(null), 4000)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}>
      <TopNav />
      <AlertStrip />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar />
        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}>
          <div style={{ flex: 1, padding: '10px 14px' }}>

            {/* Breadcrumb */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: '#687066', marginBottom: 10, padding: '6px 12px', background: '#FCFBF8', border: '1px solid #DDD8CC' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#4F5935' }}>home</span>
                <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#4F5935', fontWeight: 700, cursor: 'pointer', padding: 0, fontSize: 11 }}>Home</button>
                <span>›</span><span style={{ color: '#C58A32', fontWeight: 800 }}>Reports</span>
              </div>
              <span style={{ fontSize: 10, color: '#6F8747', fontWeight: 700, background: '#E4E8D3', padding: '2px 8px', border: '1px solid #C5D4A8' }}>● LIVE DB</span>
            </div>

            {/* Header */}
            <div style={{ background: '#4F5935', color: '#FCFBF8', padding: '10px 16px', marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800 }}>📄 OFFICIAL REPORTS — NCPOR DOCUMENT MANAGEMENT SYSTEM</div>
                <div style={{ fontSize: 10, color: '#8A9088', marginTop: 2 }}>Live data from Neon DB • GIGW 3.0 Compliant • VajraX Digital Twin Platform</div>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {/* Station filter */}
                {(['both', 'maitri', 'bharati'] as const).map(s => (
                  <button key={s} onClick={() => setSelectedStation(s)}
                    style={{ background: selectedStation === s ? '#D4883A' : 'rgba(255,255,255,0.1)', border: `2px solid ${selectedStation === s ? '#D4883A' : 'rgba(255,255,255,0.2)'}`, color: '#FCFBF8', padding: '4px 10px', fontWeight: 800, fontSize: 10, cursor: 'pointer' }}>
                    {s.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Download notification */}
            {downloadMsg && (
              <div style={{ background: downloadMsg.startsWith('✅') ? '#E4E8D3' : '#F5E8E8', border: `1px solid ${downloadMsg.startsWith('✅') ? '#C5D4A8' : '#D4A5A5'}`, padding: '8px 14px', marginBottom: 10, fontSize: 11, fontWeight: 700, color: downloadMsg.startsWith('✅') ? '#6F8747' : '#B85A5A' }}>
                {downloadMsg}
              </div>
            )}

            {/* Report Type Tabs */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 12 }}>
              {tabs.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 12px', border: `2px solid ${activeTab === tab.id ? '#4F5935' : '#E9E5DC'}`, background: activeTab === tab.id ? '#4F5935' : '#FCFBF8', color: activeTab === tab.id ? '#FCFBF8' : '#687066', cursor: 'pointer', fontWeight: activeTab === tab.id ? 800 : 600, fontSize: 11 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{tab.icon}</span>
                  <div style={{ textAlign: 'left' }}><div>{tab.label}</div><div style={{ fontSize: 9, opacity: 0.7 }}>Live from DB</div></div>
                </button>
              ))}
            </div>

            {/* Loading / Error states */}
            {isLoading && (
              <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '32px', textAlign: 'center', color: '#687066' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 32, display: 'block', marginBottom: 8 }}>hourglass_empty</span>
                Loading report data from Neon DB…
              </div>
            )}

            {error && !isLoading && (
              <div style={{ background: '#F5E8E8', border: '1px solid #D4A5A5', padding: '16px', color: '#B85A5A', fontSize: 12, fontWeight: 700 }}>
                ❌ Failed to load report. Check that the backend is running.
              </div>
            )}

            {!isLoading && !error && reportData && (
              <>
                {/* Station Status Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${stationIds.length}, 1fr)`, gap: 8, marginBottom: 12 }}>
                  {stationIds.map(sid => {
                    const info = stationsInfo?.[sid]
                    if (!info) return null
                    return (
                      <div key={sid} style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '12px 16px', position: 'relative', overflow: 'hidden' }}>
                        <div style={{ position: 'absolute', top: 0, left: 0, width: 4, height: '100%', background: info.link_state === 'UP' ? '#6F8747' : info.link_state === 'DEGRADED' ? '#C58A32' : '#B85A5A' }} />
                        <div style={{ marginLeft: 8 }}>
                          <div style={{ fontSize: 12, fontWeight: 800, color: '#4F5935' }}>{info.display_name}</div>
                          <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 10 }}>
                            <span style={{ fontWeight: 700, color: info.link_state === 'UP' ? '#6F8747' : '#C58A32' }}>● {info.link_state}</span>
                            <span style={{ color: '#B85A5A', fontWeight: 700 }}>🔴 Critical: {info.open_critical_alerts}</span>
                            <span style={{ color: '#C58A32', fontWeight: 700 }}>🟡 High: {info.open_high_alerts}</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* ── DAILY / MONTHLY: Alert Summary + Sensor Readings ── */}
                {(activeTab === 'daily' || activeTab === 'monthly') && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {/* Alert KPI row */}
                    <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px 16px' }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 10, letterSpacing: '0.05em' }}>ALERT SUMMARY — LAST 30 DAYS</div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                        {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
                          <div key={sev} style={{ border: `2px solid ${sevColor(sev)}`, padding: '10px', textAlign: 'center' }}>
                            <div style={{ fontSize: 22, fontWeight: 800, color: sevColor(sev) }}>{alertSummary?.counts_by_severity[sev] ?? 0}</div>
                            <div style={{ fontSize: 10, fontWeight: 700, color: '#687066' }}>{sev}</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Latest sensor readings per station */}
                    {stationIds.map(sid => (
                      <div key={sid} style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px 16px' }}>
                        <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 10, letterSpacing: '0.05em' }}>
                          {sid.toUpperCase()} — LATEST SENSOR READINGS &nbsp;
                          <span style={{ color: '#6F8747' }}>({sensorSummary?.[sid]?.readings_24h ?? 0} readings in last 24h)</span>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                          {(sensorSummary?.[sid]?.latest ?? []).map((s: SensorRow) => (
                            <div key={s.sensor_id} style={{ background: '#F6F3ED', border: '1px solid #E9E5DC', padding: '8px 10px' }}>
                              <div style={{ fontSize: 9, color: '#687066', fontWeight: 700, marginBottom: 2, textTransform: 'uppercase' }}>{s.sensor_id.split('.').slice(-2).join(' › ')}</div>
                              <div style={{ fontSize: 16, fontWeight: 800, color: '#252820' }}>{s.value.toFixed(2)} <span style={{ fontSize: 10, color: '#687066' }}>{s.unit}</span></div>
                            </div>
                          ))}
                          {(sensorSummary?.[sid]?.latest ?? []).length === 0 && (
                            <div style={{ color: '#8A9088', fontSize: 11, gridColumn: '1/-1' }}>No recent sensor data — run refresh_sensor_readings.py</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── INCIDENT: Alert List ── */}
                {activeTab === 'incident' && (
                  <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px 16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 10, letterSpacing: '0.05em' }}>
                      RECENT ALERTS — LAST 30 DAYS ({alertSummary?.total_last_30d ?? 0} total)
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {(alertSummary?.recent ?? []).map((a: AlertRow) => (
                        <div key={a.alert_id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', background: '#F6F3ED', border: '1px solid #E9E5DC' }}>
                          <span style={{ fontWeight: 800, fontSize: 10, color: sevColor(a.severity), background: '#FCFBF8', border: `1px solid ${sevColor(a.severity)}`, padding: '2px 8px', flexShrink: 0 }}>{a.severity}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 700, fontSize: 12, color: '#252820', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.description}</div>
                            <div style={{ fontSize: 10, color: '#687066', marginTop: 2 }}>
                              {new Date(a.triggered_at).toLocaleString('en-IN')} &nbsp;•&nbsp; Domain: {a.domain} &nbsp;•&nbsp; {a.ack_state}
                            </div>
                          </div>
                        </div>
                      ))}
                      {(alertSummary?.recent ?? []).length === 0 && (
                        <div style={{ color: '#8A9088', fontSize: 11, padding: 16, textAlign: 'center' }}>No alerts in the last 30 days.</div>
                      )}
                    </div>
                  </div>
                )}

                {/* ── SCIENTIFIC: Sensor data per domain ── */}
                {activeTab === 'scientific' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {stationIds.map(sid => (
                      <div key={sid} style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px 16px' }}>
                        <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 12, letterSpacing: '0.05em' }}>
                          {sid.toUpperCase()} — FULL SENSOR DATASET
                        </div>
                        {/* Group by domain */}
                        {['energy', 'weather', 'seismic'].map(domain => {
                          const sensors = (sensorSummary?.[sid]?.latest ?? []).filter((s: SensorRow) => s.domain === domain)
                          if (!sensors.length) return null
                          return (
                            <div key={domain} style={{ marginBottom: 12 }}>
                              <div style={{ fontSize: 10, fontWeight: 800, color: '#4F5935', marginBottom: 6, textTransform: 'uppercase' }}>[{domain}]</div>
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
                                {sensors.map((s: SensorRow) => (
                                  <div key={s.sensor_id} style={{ background: '#F6F3ED', border: '1px solid #E9E5DC', padding: '8px 10px' }}>
                                    <div style={{ fontSize: 9, color: '#687066', fontWeight: 700, marginBottom: 2 }}>{s.sensor_id.split('.').slice(-1)[0].replace(/_/g, ' ').toUpperCase()}</div>
                                    <div style={{ fontSize: 18, fontWeight: 800, color: '#252820' }}>{s.value.toFixed(3)} <span style={{ fontSize: 10, color: '#687066' }}>{s.unit}</span></div>
                                    <div style={{ fontSize: 9, color: '#8A9088', marginTop: 2 }}>{new Date(s.ts).toLocaleTimeString('en-IN')}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ))}
                  </div>
                )}

                {/* ── AUDIT: Inventory + Assets ── */}
                {activeTab === 'audit' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {stationIds.map(sid => (
                      <div key={sid}>
                        {/* Inventory */}
                        <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px 16px', marginBottom: 8 }}>
                          <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 10, letterSpacing: '0.05em' }}>{sid.toUpperCase()} — INVENTORY AUDIT</div>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                            <thead>
                              <tr style={{ background: '#F6F3ED', fontSize: 10, textAlign: 'left' }}>
                                {['Item', 'Category', 'Quantity', 'Unit', 'Days Left', 'Status'].map(h => (
                                  <th key={h} style={{ padding: '6px 10px', fontWeight: 700, color: '#687066', borderBottom: '2px solid #E9E5DC' }}>{h}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {(inventory?.[sid] ?? []).map((item: InventoryRow) => (
                                <tr key={item.name} style={{ borderBottom: '1px solid #F6F3ED' }}>
                                  <td style={{ padding: '7px 10px', fontWeight: 600, color: '#252820' }}>{item.name}</td>
                                  <td style={{ padding: '7px 10px', color: '#687066' }}>{item.category}</td>
                                  <td style={{ padding: '7px 10px', fontWeight: 700, color: '#4F5935' }}>{item.quantity.toLocaleString()}</td>
                                  <td style={{ padding: '7px 10px', color: '#687066' }}>{item.unit}</td>
                                  <td style={{ padding: '7px 10px', color: item.days_remaining && item.days_remaining < 30 ? '#B85A5A' : '#6F8747', fontWeight: 700 }}>
                                    {item.days_remaining ?? '—'}
                                  </td>
                                  <td style={{ padding: '7px 10px' }}>
                                    <span style={{ fontSize: 9, fontWeight: 800, color: statusColor(item.status), background: '#F6F3ED', padding: '2px 6px', border: '1px solid #E9E5DC' }}>{item.status}</span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        {/* Assets */}
                        <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px 16px' }}>
                          <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 10, letterSpacing: '0.05em' }}>{sid.toUpperCase()} — ASSET REGISTER</div>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
                            {(assets?.[sid] ?? []).map((a: AssetRow) => (
                              <div key={a.name} style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#F6F3ED', border: '1px solid #E9E5DC', padding: '8px 12px' }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#4F5935' }}>location_on</span>
                                <div>
                                  <div style={{ fontWeight: 700, fontSize: 11, color: '#252820' }}>{a.name}</div>
                                  <div style={{ fontSize: 9, color: '#687066' }}>{a.asset_type.replace(/_/g, ' ')} &nbsp;•&nbsp; <span style={{ color: statusColor(a.status), fontWeight: 700 }}>{a.status}</span></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Download Button */}
                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px 16px', marginTop: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 10, color: '#687066' }}>
                    Report generated from live Neon DB &nbsp;•&nbsp; Generated: {reportData?.generated_at ? new Date(reportData.generated_at as string).toLocaleString('en-IN') : '—'}
                  </div>
                  <button
                    onClick={handleDownload}
                    disabled={isDownloading}
                    style={{ display: 'flex', alignItems: 'center', gap: 6, background: isDownloading ? '#8A9088' : '#4F5935', color: '#FCFBF8', border: 'none', padding: '8px 18px', cursor: isDownloading ? 'not-allowed' : 'pointer', fontWeight: 800, fontSize: 11 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>download</span>
                    {isDownloading ? 'Generating…' : `Download ${activeTab.toUpperCase()} Report (.txt)`}
                  </button>
                </div>
              </>
            )}

            {/* Footer info bar */}
            <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '12px 16px', marginTop: 8 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 6, letterSpacing: '0.05em' }}>DOCUMENT MANAGEMENT SYSTEM INFO</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, fontSize: 10 }}>
                {[{ label: 'Repository', value: 'Neon PostgreSQL (Live)', icon: 'cloud' }, { label: 'Encryption', value: 'AES-256 at rest & transit', icon: 'lock' }, { label: 'Digital Signatures', value: 'PKI / eSign (MeITY)', icon: 'verified' }, { label: 'Retention Policy', value: 'Daily: 90d • Monthly: 10yr', icon: 'history' }].map(info => (
                  <div key={info.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#4F5935' }}>{info.icon}</span>
                    <div><div style={{ fontWeight: 700, color: '#4F5935' }}>{info.label}</div><div style={{ color: '#687066' }}>{info.value}</div></div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </main>
      </div>
      <Footer />
    </div>
  )
}
