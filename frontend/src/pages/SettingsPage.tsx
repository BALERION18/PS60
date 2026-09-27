import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import { useAuth } from '../hooks/useAuth'

type TabType = 'system' | 'security' | 'link' | 'users' | 'notifications'

export default function SettingsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('system')

  // Settings state
  const [telemetryInterval, setTelemetryInterval] = useState('10')
  const [alertRetention, setAlertRetention] = useState('90')
  const [syncMode, setSyncMode] = useState('adaptive')
  const [mqttQos, setMqttQos] = useState('1')
  const [blackboxDepth, setBlackboxDepth] = useState('72')
  const [sessionTimeout, setSessionTimeout] = useState('60')
  const [twoFactor, setTwoFactor] = useState(true)
  const [auditLog, setAuditLog] = useState(true)
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [smsAlerts, setSmsAlerts] = useState(true)
  const [criticalPush, setCriticalPush] = useState(true)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  function handleSave() {
    setSaveMsg(`[${new Date().toLocaleTimeString('en-GB')}] Settings saved and applied. Configuration synced to both station edge nodes via MQTT. Ref: NCPOR/SETTINGS/2026/${Date.now()}`)
    setTimeout(() => setSaveMsg(null), 5000)
  }

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'system', label: 'System Config', icon: 'settings' },
    { id: 'security', label: 'Security & Access', icon: 'security' },
    { id: 'link', label: 'Satellite Link', icon: 'satellite_alt' },
    { id: 'users', label: 'User Management', icon: 'manage_accounts' },
    { id: 'notifications', label: 'Notifications', icon: 'notifications' },
  ]

  function Toggle({ on, onToggle, label }: { on: boolean; onToggle: () => void; label: string }) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #f1f5f9' }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#1e293b' }}>{label}</span>
        <button onClick={onToggle} style={{ width: 42, height: 22, background: on ? '#0b3b60' : '#cbd5e1', border: 'none', cursor: 'pointer', position: 'relative', transition: 'background 0.2s', borderRadius: 11 }}>
          <div style={{ position: 'absolute', top: 3, left: on ? 22 : 3, width: 16, height: 16, background: '#fff', borderRadius: '50%', transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }} />
        </button>
      </div>
    )
  }

  function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] }) {
    return (
      <div style={{ padding: '10px 0', borderBottom: '1px solid #f1f5f9' }}>
        <label style={{ fontSize: 11, fontWeight: 700, color: '#64748b', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</label>
        <select value={value} onChange={e => onChange(e.target.value)} style={{ width: '100%', padding: '7px 10px', border: '1px solid #cbd5e1', fontSize: 12, fontFamily: 'Inter', background: '#f8fafc', color: '#1e293b', outline: 'none' }}>
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
    )
  }

  function NumberField({ label, value, onChange, unit, min, max }: { label: string; value: string; onChange: (v: string) => void; unit: string; min: number; max: number }) {
    return (
      <div style={{ padding: '10px 0', borderBottom: '1px solid #f1f5f9' }}>
        <label style={{ fontSize: 11, fontWeight: 700, color: '#64748b', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="number" value={value} onChange={e => onChange(e.target.value)} min={min} max={max} style={{ flex: 1, padding: '7px 10px', border: '1px solid #cbd5e1', fontSize: 12, fontFamily: 'Inter', background: '#f8fafc', color: '#1e293b', outline: 'none' }} />
          <span style={{ fontSize: 12, color: '#64748b', fontWeight: 600 }}>{unit}</span>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
      <TopNav />
      <AlertStrip />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar />
        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
          <div style={{ flex: 1, padding: '10px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: '#64748b', marginBottom: 10, padding: '6px 12px', background: '#fff', border: '1px solid #cbd5e1' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#0b3b60' }}>home</span>
                <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#0b3b60', fontWeight: 700, cursor: 'pointer', padding: 0, fontSize: 11 }}>Home</button>
                <span>›</span><span style={{ color: '#ea580c', fontWeight: 800 }}>System Settings</span>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: '#16a34a', fontWeight: 700, background: '#f0fdf4', padding: '2px 8px', border: '1px solid #bbf7d0' }}>ADMIN: {user?.username?.toUpperCase()}</span>
              </div>
            </div>

            <div style={{ background: '#0b3b60', color: '#fff', padding: '10px 16px', marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800 }}>⚙️ SYSTEM SETTINGS — VAJRAX DIGITAL TWIN PLATFORM v3.02</div>
                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>Administrator configuration console • NIC GOI Secured • Changes logged in immutable audit trail</div>
              </div>
              <div style={{ fontSize: 10, color: '#ff9933', fontWeight: 700 }}>🔒 ADMIN ACCESS LEVEL</div>
            </div>

            {saveMsg && (
              <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '10px 14px', marginBottom: 10, fontSize: 11, fontWeight: 700, color: '#16a34a' }}>
                {saveMsg}
              </div>
            )}

            <div style={{ display: 'flex', gap: 14 }}>
              {/* Left Tab Nav */}
              <div style={{ width: 180, flexShrink: 0 }}>
                <div style={{ background: '#fff', border: '1px solid #e2e8f0' }}>
                  {tabs.map(tab => (
                    <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{ display: 'flex', width: '100%', alignItems: 'center', gap: 8, padding: '10px 12px', border: 'none', background: activeTab === tab.id ? '#f0f9ff' : 'transparent', cursor: 'pointer', fontWeight: activeTab === tab.id ? 800 : 600, color: activeTab === tab.id ? '#0b3b60' : '#475569', fontSize: 11, borderLeft: activeTab === tab.id ? '3px solid #0b3b60' : '3px solid transparent', borderBottom: '1px solid #f1f5f9', textAlign: 'left' }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{tab.icon}</span>
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* System Status Box */}
                <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '12px', marginTop: 12 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 8, letterSpacing: '0.05em' }}>SYSTEM STATUS</div>
                  {[{ label: 'Platform Version', value: 'v3.02' },{ label: 'Edge Node (Maitri)', value: 'ONLINE', color: '#16a34a' },{ label: 'Edge Node (Bharati)', value: 'ONLINE', color: '#16a34a' },{ label: 'Cloud Backend', value: 'HEALTHY', color: '#16a34a' },{ label: 'Last Config Sync', value: '8 min ago' }].map(s => (
                    <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #f8fafc', fontSize: 10 }}>
                      <span style={{ color: '#64748b' }}>{s.label}</span>
                      <span style={{ fontWeight: 800, color: (s as any).color || '#0f172a' }}>{s.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Content Area */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {activeTab === 'system' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '20px' }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#0b3b60', marginBottom: 16, paddingBottom: 8, borderBottom: '2px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>tune</span>TELEMETRY & DATA SETTINGS
                      </div>
                      <SelectField label="Sensor Polling Interval" value={telemetryInterval} onChange={setTelemetryInterval} options={[{ value: '5', label: '5 seconds (High Frequency)' },{ value: '10', label: '10 seconds (Standard — Recommended)' },{ value: '30', label: '30 seconds (Low Bandwidth)' },{ value: '60', label: '60 seconds (Minimal)' }]} />
                      <NumberField label="Alert Retention Period (days)" value={alertRetention} onChange={setAlertRetention} unit="days" min={30} max={365} />
                      <SelectField label="Data Compression Algorithm" value="zstd" onChange={() => {}} options={[{ value: 'zstd', label: 'Zstandard (zstd) — Default & Recommended' },{ value: 'lz4', label: 'LZ4 — Maximum Speed' },{ value: 'none', label: 'No Compression' }]} />
                      <NumberField label="Black Box Logger Depth" value={blackboxDepth} onChange={setBlackboxDepth} unit="hours" min={24} max={168} />
                    </div>

                    <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '20px' }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#0b3b60', marginBottom: 16, paddingBottom: 8, borderBottom: '2px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>info</span>PLATFORM INFORMATION
                      </div>
                      {[{ label: 'Platform Name', value: 'VajraX Antarctic Digital Twin v3.02' },{ label: 'Operator Organisation', value: 'National Centre for Polar and Ocean Research (NCPOR)' },{ label: 'Ministry', value: 'Ministry of Earth Sciences, Government of India' },{ label: 'Developed By', value: 'NIC India | NCPOR Polar Technology Group' },{ label: 'Certification', value: 'GIGW 3.0 Compliant • CERT-In Audited' },{ label: 'Data Classification', value: 'RESTRICTED / OFFICIAL USE ONLY' }].map(info => (
                        <div key={info.label} style={{ display: 'flex', gap: 12, padding: '7px 0', borderBottom: '1px solid #f8fafc', fontSize: 11 }}>
                          <span style={{ color: '#64748b', width: 200, flexShrink: 0 }}>{info.label}</span>
                          <span style={{ fontWeight: 700, color: '#1e293b' }}>{info.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeTab === 'security' && (
                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '20px' }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0b3b60', marginBottom: 16, paddingBottom: 8, borderBottom: '2px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>security</span>SECURITY CONFIGURATION
                    </div>
                    <SelectField label="Session Timeout" value={sessionTimeout} onChange={setSessionTimeout} options={[{ value: '30', label: '30 minutes' },{ value: '60', label: '60 minutes (Default)' },{ value: '120', label: '2 hours' },{ value: '480', label: '8 hours (Low Security)' }]} />
                    <Toggle on={twoFactor} onToggle={() => setTwoFactor(v => !v)} label="Enable Two-Factor Authentication (TOTP / eSign)" />
                    <Toggle on={auditLog} onToggle={() => setAuditLog(v => !v)} label="Immutable Audit Log (Mandatory for GOI Portals)" />
                    <Toggle on={true} onToggle={() => {}} label="TLS 1.3 Enforcement on All Connections" />
                    <Toggle on={true} onToggle={() => {}} label="mTLS Station-to-Cloud Authentication (Ed25519)" />
                    <Toggle on={true} onToggle={() => {}} label="CSRF Token Validation" />
                    <div style={{ margin: '16px 0', background: '#f0f9ff', border: '1px solid #bae6fd', padding: '12px' }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#0b3b60', marginBottom: 6 }}>🔑 ENCRYPTION KEY STATUS</div>
                      {[{ name: 'JWT Signing Key (HS256)', expiry: '2026-12-31', status: 'VALID' },{ name: 'Station Maitri Ed25519 Keypair', expiry: '2027-01-01', status: 'VALID' },{ name: 'Station Bharati Ed25519 Keypair', expiry: '2027-01-01', status: 'VALID' },{ name: 'TLS Certificate (*.ncpor.gov.in)', expiry: '2027-06-30', status: 'VALID' }].map(k => (
                        <div key={k.name} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '4px 0', borderBottom: '1px solid #e2e8f0' }}>
                          <span style={{ color: '#475569' }}>{k.name}</span>
                          <div style={{ display: 'flex', gap: 12 }}>
                            <span style={{ color: '#64748b' }}>Expires: {k.expiry}</span>
                            <span style={{ fontWeight: 800, color: '#16a34a' }}>✓ {k.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeTab === 'link' && (
                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '20px' }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0b3b60', marginBottom: 16, paddingBottom: 8, borderBottom: '2px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>satellite_alt</span>SATELLITE LINK CONFIGURATION
                    </div>
                    <SelectField label="Sync Mode" value={syncMode} onChange={setSyncMode} options={[{ value: 'adaptive', label: 'Adaptive (AI-optimised based on link quality) — Recommended' },{ value: 'scheduled', label: 'Scheduled (Fixed time windows)' },{ value: 'continuous', label: 'Continuous (Maximum bandwidth use)' },{ value: 'manual', label: 'Manual (Operator-triggered only)' }]} />
                    <SelectField label="MQTT QoS Level" value={mqttQos} onChange={setMqttQos} options={[{ value: '0', label: 'QoS 0 — At most once (Fire & forget)' },{ value: '1', label: 'QoS 1 — At least once (Default)' },{ value: '2', label: 'QoS 2 — Exactly once (Critical data only)' }]} />
                    <SelectField label="Alert Priority Lane (QoS 2 Override)" value="critical_high" onChange={() => {}} options={[{ value: 'critical_high', label: 'CRITICAL + HIGH severity (Recommended)' },{ value: 'critical', label: 'CRITICAL only' },{ value: 'all', label: 'All alerts (High bandwidth)' }]} />
                    <NumberField label="Link Heartbeat Interval" value="60" onChange={() => {}} unit="seconds" min={30} max={300} />
                    <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      {['maitri', 'bharati'].map(s => (
                        <div key={s} style={{ border: '1px solid #e2e8f0', padding: '12px', background: '#f8fafc' }}>
                          <div style={{ fontSize: 10, fontWeight: 800, color: '#0b3b60', marginBottom: 6 }}>📡 {s.toUpperCase()} VSAT STATUS</div>
                          {[{ label: 'Link State', value: s === 'maitri' ? 'UP' : 'DEGRADED', color: s === 'maitri' ? '#16a34a' : '#d97706' },{ label: 'Signal Margin', value: s === 'maitri' ? '8.4 dB' : '12.4 dB' },{ label: 'Bandwidth', value: s === 'maitri' ? '2.1 Mbps ↑/↓' : '4.8 Mbps ↑/↓' },{ label: 'Queue Depth', value: s === 'maitri' ? '0 bytes' : '1.2 KB' }].map(v => (
                            <div key={v.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '3px 0', borderBottom: '1px solid #f1f5f9' }}>
                              <span style={{ color: '#64748b' }}>{v.label}</span>
                              <span style={{ fontWeight: 800, color: (v as any).color || '#0f172a' }}>{v.value}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeTab === 'users' && (
                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '20px' }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0b3b60', marginBottom: 16, paddingBottom: 8, borderBottom: '2px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>manage_accounts</span>USER MANAGEMENT — NCPOR POLAR OPERATIONS WING
                      </div>
                      <button style={{ background: '#0b3b60', color: '#fff', border: 'none', padding: '4px 12px', fontSize: 10, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 13 }}>person_add</span>Add User
                      </button>
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                      <thead>
                        <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
                          {['Username', 'Full Name', 'Role', 'Station Access', 'Status', 'Last Login', 'Actions'].map(h => (
                            <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: '#64748b' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[{ username: 'admin', name: 'NCPOR Administrator', role: 'ADMIN', access: 'All Stations', status: 'ACTIVE', lastLogin: '2026-09-02 14:12' },{ username: 'operator', name: 'Ops. Command Centre', role: 'OPERATOR', access: 'Maitri + Bharati', status: 'ACTIVE', lastLogin: '2026-09-02 09:45' },{ username: 's.kumar.ncpor', name: 'Dr. Sanjay Kumar', role: 'SCIENTIST', access: 'Read Only', status: 'ACTIVE', lastLogin: '2026-09-01 18:22' },{ username: 'station.maitri', name: 'Maitri Station Node', role: 'EDGE_NODE', access: 'Maitri Only', status: 'ACTIVE', lastLogin: '2026-09-02 14:10' },{ username: 'station.bharati', name: 'Bharati Station Node', role: 'EDGE_NODE', access: 'Bharati Only', status: 'ACTIVE', lastLogin: '2026-09-02 14:08' }].map((u, i) => (
                          <tr key={u.username} style={{ borderBottom: '1px solid #f1f5f9', background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                            <td style={{ padding: '8px 10px', fontWeight: 800, color: '#0b3b60' }}>{u.username}</td>
                            <td style={{ padding: '8px 10px', fontWeight: 600, color: '#1e293b' }}>{u.name}</td>
                            <td style={{ padding: '8px 10px' }}>
                              <span style={{ fontSize: 10, fontWeight: 800, color: u.role === 'ADMIN' ? '#dc2626' : u.role === 'OPERATOR' ? '#d97706' : u.role === 'EDGE_NODE' ? '#7c3aed' : '#0b3b60', background: '#f8fafc', padding: '2px 6px', border: '1px solid #e2e8f0' }}>{u.role}</span>
                            </td>
                            <td style={{ padding: '8px 10px', color: '#64748b' }}>{u.access}</td>
                            <td style={{ padding: '8px 10px' }}>
                              <span style={{ fontWeight: 800, fontSize: 10, color: '#16a34a', background: '#f0fdf4', padding: '2px 6px', border: '1px solid #bbf7d0' }}>{u.status}</span>
                            </td>
                            <td style={{ padding: '8px 10px', color: '#94a3b8', fontSize: 10 }}>{u.lastLogin}</td>
                            <td style={{ padding: '8px 10px' }}>
                              <div style={{ display: 'flex', gap: 4 }}>
                                <button style={{ background: 'none', border: '1px solid #e2e8f0', color: '#0b3b60', padding: '3px 6px', cursor: 'pointer', fontSize: 10 }}>Edit</button>
                                {u.role !== 'ADMIN' && <button style={{ background: 'none', border: '1px solid #fecaca', color: '#dc2626', padding: '3px 6px', cursor: 'pointer', fontSize: 10 }}>Reset</button>}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {activeTab === 'notifications' && (
                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '20px' }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#0b3b60', marginBottom: 16, paddingBottom: 8, borderBottom: '2px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>notifications</span>NOTIFICATION PREFERENCES
                    </div>
                    <Toggle on={emailAlerts} onToggle={() => setEmailAlerts(v => !v)} label="Email Alerts — Critical & High severity (ncpor.gov.in)" />
                    <Toggle on={smsAlerts} onToggle={() => setSmsAlerts(v => !v)} label="SMS Alerts — Critical severity (NCPOR HQ registered numbers)" />
                    <Toggle on={criticalPush} onToggle={() => setCriticalPush(v => !v)} label="In-Portal Push Notifications — All alerts" />
                    <Toggle on={true} onToggle={() => {}} label="Daily Operations Summary Email (06:00 IST)" />
                    <Toggle on={false} onToggle={() => {}} label="WeekLy Analytics Digest" />
                    <Toggle on={true} onToggle={() => {}} label="Satellite Link Status Change Alerts" />
                    <Toggle on={true} onToggle={() => {}} label="Maintenance Due Reminders (72h advance)" />
                    <div style={{ marginTop: 16, background: '#f8fafc', border: '1px solid #e2e8f0', padding: '12px' }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 8, letterSpacing: '0.05em' }}>NOTIFICATION DISTRIBUTION LIST</div>
                      {[{ role: 'CRITICAL Alerts', recipients: 'Station Commander, NCPOR Director, MoES Duty Officer', channel: 'Email + SMS + Portal' },{ role: 'HIGH Alerts', recipients: 'Station Commander, Chief Engineer, NCPOR HQ Ops', channel: 'Email + Portal' },{ role: 'Daily Reports', recipients: 'NCPOR Director, MoES Secretary (Polar)', channel: 'Email' },{ role: 'Maintenance', recipients: 'Chief Engineer, NCPOR Logistics', channel: 'Email + Portal' }].map(d => (
                        <div key={d.role} style={{ padding: '7px 0', borderBottom: '1px solid #f1f5f9', fontSize: 11 }}>
                          <div style={{ fontWeight: 800, color: '#0b3b60', marginBottom: 2 }}>{d.role}</div>
                          <div style={{ color: '#475569' }}>{d.recipients}</div>
                          <div style={{ color: '#94a3b8', fontSize: 10, marginTop: 2 }}>Channel: {d.channel}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
                  <button style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', color: '#475569', padding: '8px 18px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>
                    Reset to Defaults
                  </button>
                  <button onClick={handleSave} style={{ background: '#0b3b60', border: 'none', color: '#fff', padding: '8px 20px', fontSize: 11, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 14 }}>save</span>Save & Apply Settings
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  )
}
