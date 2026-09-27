import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import { useAnalytics } from '../hooks/useAnalytics'

type StationId = 'maitri' | 'bharati'
type TabType = 'fuel' | 'energy' | 'anomaly' | 'maintenance' | 'expedition'

function KpiCard({ label, value, unit, icon, color, trend, sub }: { label: string; value: string | number; unit?: string; icon: string; color: string; trend?: string; sub?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '14px', position: 'relative', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, width: 3, height: '100%', background: color }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginLeft: 8 }}>
        <div>
          <div style={{ fontSize: 9.5, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
          <div style={{ marginTop: 6 }}>
            <span style={{ fontSize: 22, fontWeight: 800, color: '#0f172a' }}>{value}</span>
            {unit && <span style={{ fontSize: 11, color: '#64748b', marginLeft: 3 }}>{unit}</span>}
          </div>
          {sub && <div style={{ fontSize: 9.5, color: '#94a3b8', marginTop: 3 }}>{sub}</div>}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 20, color }}>{icon}</span>
          {trend && <span style={{ fontSize: 10, fontWeight: 700, color: trend.startsWith('▲') ? '#16a34a' : '#dc2626' }}>{trend}</span>}
        </div>
      </div>
    </div>
  )
}

function MiniBarChart({ data, labels, color }: { data: number[]; labels: string[]; color: string }) {
  const max = Math.max(...data, 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 60 }}>
      {data.map((v, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <div style={{ width: '100%', height: `${(v / max) * 52}px`, background: color, opacity: i === data.length - 1 ? 1 : 0.5, transition: 'height 0.3s' }} />
          <span style={{ fontSize: 8, color: '#94a3b8' }}>{labels[i]}</span>
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const navigate = useNavigate()
  const [activeStation, setActiveStation] = useState<StationId>('maitri')
  const [activeTab, setActiveTab] = useState<TabType>('fuel')
  useAnalytics(activeStation)

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'fuel', label: 'Fuel Burn Model', icon: 'local_gas_station' },
    { id: 'energy', label: 'Energy Forecast', icon: 'bolt' },
    { id: 'anomaly', label: 'Anomaly Detection', icon: 'psychology' },
    { id: 'maintenance', label: 'Predictive Maintenance', icon: 'build' },
    { id: 'expedition', label: 'Expedition Planning', icon: 'explore' },
  ]

  const fuel = activeStation === 'maitri'
    ? { remaining: 138400, capacity: 165000, dailyBurn: 1240, resupplyDate: '2027-02-15', daysLeft: 111, trend: '▼ -2.4%' }
    : { remaining: 210500, capacity: 250000, dailyBurn: 1680, resupplyDate: '2027-03-20', daysLeft: 125, trend: '▼ -1.8%' }
  const fuelPct = Math.round((fuel.remaining / fuel.capacity) * 100)
  const burnHistory = [1210, 1280, 1190, 1320, 1260, 1240, fuel.dailyBurn]
  const burnLabels = ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', 'Today']

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
      <TopNav />
      <AlertStrip />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar activeStation={activeStation} onSwitchStation={() => setActiveStation(s => s === 'maitri' ? 'bharati' : 'maitri')} />
        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
          <div style={{ flex: 1, padding: '10px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: '#64748b', marginBottom: 10, padding: '6px 12px', background: '#fff', border: '1px solid #cbd5e1' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#0b3b60' }}>home</span>
                <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#0b3b60', fontWeight: 700, cursor: 'pointer', padding: 0, fontSize: 11 }}>Home</button>
                <span>›</span><span style={{ color: '#ea580c', fontWeight: 800 }}>Predictive Analytics</span>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: '#7c3aed', fontWeight: 700, background: '#f5f3ff', padding: '2px 8px', border: '1px solid #ddd6fe' }}>🤖 AI ENGINE ACTIVE</span>
              </div>
            </div>

            <div style={{ background: 'linear-gradient(135deg, #0b3b60 0%, #1a5276 100%)', color: '#fff', padding: '12px 16px', marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800 }}>🤖 PREDICTIVE ANALYTICS — {activeStation === 'maitri' ? 'MAITRI' : 'BHARATI'} AI ENGINE v2.1</div>
                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>Edge AI • LSTM Burn Models • Anomaly Detection • Maintenance Forecasting • Mission Planning</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {(['maitri', 'bharati'] as const).map(s => (
                  <button key={s} onClick={() => setActiveStation(s)} style={{ background: activeStation === s ? '#ff9933' : 'rgba(255,255,255,0.1)', border: activeStation === s ? '2px solid #ff9933' : '2px solid rgba(255,255,255,0.2)', color: '#fff', padding: '4px 12px', fontWeight: 800, fontSize: 10, cursor: 'pointer' }}>{s.toUpperCase()}</button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', borderBottom: '2px solid #cbd5e1', marginBottom: 12, background: '#fff', padding: '0 8px' }}>
              {tabs.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '8px 14px', border: 'none', background: 'none', cursor: 'pointer', fontWeight: activeTab === tab.id ? 800 : 600, color: activeTab === tab.id ? '#0b3b60' : '#64748b', fontSize: 11, borderBottom: activeTab === tab.id ? '2px solid #0b3b60' : '2px solid transparent', marginBottom: -2 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 15 }}>{tab.icon}</span>{tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'fuel' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="FUEL REMAINING" value={fuel.remaining.toLocaleString()} unit="L" icon="local_gas_station" color="#ea580c" sub={`${fuelPct}% of ${(fuel.capacity / 1000).toFixed(0)}kL capacity`} />
                  <KpiCard label="DAILY BURN RATE" value={fuel.dailyBurn.toLocaleString()} unit="L/day" icon="whatshot" color="#dc2626" trend={fuel.trend} sub="7-day rolling average" />
                  <KpiCard label="DAYS OF AUTONOMY" value={fuel.daysLeft} unit="days" icon="calendar_month" color="#0b3b60" sub="Until empty at current burn" />
                  <KpiCard label="NEXT RESUPPLY" value={fuel.resupplyDate} icon="local_shipping" color="#16a34a" sub="Scheduled supply voyage" />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 14, letterSpacing: '0.05em' }}>FUEL TANK LEVEL — VISUAL GAUGE</div>
                    <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
                      <div style={{ width: 60, height: 120, border: '2px solid #cbd5e1', position: 'relative', background: '#f8fafc', overflow: 'hidden' }}>
                        <div style={{ position: 'absolute', bottom: 0, width: '100%', height: `${fuelPct}%`, background: fuelPct > 50 ? '#16a34a' : fuelPct > 25 ? '#d97706' : '#dc2626', transition: 'height 0.5s', opacity: 0.8 }} />
                        <div style={{ position: 'absolute', bottom: '25%', width: '100%', borderTop: '1px dashed #dc2626', opacity: 0.5 }} />
                        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: 11, fontWeight: 800, color: '#0f172a' }}>{fuelPct}%</div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#0b3b60', marginBottom: 8 }}>AI BURN RATE PREDICTION — LSTM MODEL</div>
                        <div style={{ fontSize: 10, lineHeight: 1.6, color: '#475569' }}>
                          Based on current weather conditions (temp: {activeStation === 'maitri' ? '-28.4' : '-21.7'}°C), crew occupancy ({activeStation === 'maitri' ? 24 : 32}), and generator load, the LSTM model predicts:
                        </div>
                        <div style={{ margin: '10px 0', display: 'flex', flexDirection: 'column', gap: 5 }}>
                          {[{ label: 'Next 7 days', val: `${fuel.dailyBurn} \u00b1 45 L/day`, icon: 'trending_flat' },{ label: 'Next 30 days', val: `${Math.round(fuel.dailyBurn * 1.04)} \u00b1 80 L/day`, icon: 'trending_up' },{ label: 'Winter Peak (Jul-Aug)', val: `${Math.round(fuel.dailyBurn * 1.18)} \u00b1 120 L/day`, icon: 'trending_up' }].map(p => (
                            <div key={p.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
                              <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#ea580c' }}>{p.icon}</span>
                              <span style={{ color: '#64748b' }}>{p.label}:</span>
                              <span style={{ fontWeight: 800, color: '#0f172a' }}>{p.val}</span>
                            </div>
                          ))}
                        </div>
                        <div style={{ background: '#fef3c7', border: '1px solid #f59e0b', padding: '6px 10px', fontSize: 10, color: '#92400e', fontWeight: 700 }}>
                          ⚠ Model confidence: 91.4% • Last trained: 2026-09-01 02:00 UTC
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 14, letterSpacing: '0.05em' }}>DAILY FUEL BURN — LAST 7 DAYS (Litres)</div>
                    <MiniBarChart data={burnHistory} labels={burnLabels} color="#ea580c" />
                    <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 10 }}>
                      <div style={{ background: '#fef3c7', padding: '8px', textAlign: 'center' }}>
                        <div style={{ fontWeight: 800, color: '#d97706', fontSize: 13 }}>{Math.max(...burnHistory).toLocaleString()}</div>
                        <div style={{ color: '#64748b' }}>Peak (7d)</div>
                      </div>
                      <div style={{ background: '#f0fdf4', padding: '8px', textAlign: 'center' }}>
                        <div style={{ fontWeight: 800, color: '#16a34a', fontSize: 13 }}>{Math.min(...burnHistory).toLocaleString()}</div>
                        <div style={{ color: '#64748b' }}>Min (7d)</div>
                      </div>
                      <div style={{ background: '#f0f9ff', padding: '8px', textAlign: 'center' }}>
                        <div style={{ fontWeight: 800, color: '#0b3b60', fontSize: 13 }}>{Math.round(burnHistory.reduce((a, b) => a + b) / burnHistory.length).toLocaleString()}</div>
                        <div style={{ color: '#64748b' }}>Avg (7d)</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'energy' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="CURRENT LOAD" value={activeStation === 'maitri' ? 164 : 218} unit="kW" icon="bolt" color="#f59e0b" sub="Real-time station demand" />
                  <KpiCard label="SOLAR GENERATION" value={activeStation === 'maitri' ? '18.5' : '34.0'} unit="kW" icon="wb_sunny" color="#16a34a" trend="▲ +12%" />
                  <KpiCard label="WIND GENERATION" value={activeStation === 'maitri' ? '24.2' : '16.8'} unit="kW" icon="air" color="#3b82f6" trend="▲ +8%" />
                  <KpiCard label="BATTERY SoC" value={activeStation === 'maitri' ? 91 : 96} unit="%" icon="battery_charging_full" color="#16a34a" sub="LiFePO4 bank" />
                </div>
                <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 14, letterSpacing: '0.05em' }}>48-HOUR ENERGY BALANCE FORECAST — MICROGRID AI MODEL</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 4 }}>
                    {Array.from({ length: 8 }).map((_, i) => {
                      const load = 150 + Math.sin(i * 0.8) * 30 + 20
                      const solar = i >= 2 && i <= 6 ? 15 + Math.sin((i - 2) * 0.7) * 18 : 0
                      const wind = 20 + Math.sin(i * 0.5) * 8
                      const gen = Math.max(0, load - solar - wind)
                      return (
                        <div key={i} style={{ textAlign: 'center', border: '1px solid #e2e8f0', padding: '8px 4px', background: '#fafafa' }}>
                          <div style={{ fontSize: 9, color: '#94a3b8', marginBottom: 4 }}>+{i * 6}h</div>
                          <div style={{ fontSize: 10, fontWeight: 800, color: '#0b3b60' }}>{Math.round(load)}kW</div>
                          <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <div style={{ height: 4, background: '#16a34a', width: `${solar / load * 100}%` }} title={`Solar: ${Math.round(solar)}kW`} />
                            <div style={{ height: 4, background: '#3b82f6', width: `${wind / load * 100}%` }} title={`Wind: ${Math.round(wind)}kW`} />
                            <div style={{ height: 4, background: '#ea580c', width: `${gen / load * 100}%` }} title={`Generator: ${Math.round(gen)}kW`} />
                          </div>
                          <div style={{ fontSize: 8, color: '#64748b', marginTop: 4 }}>G:{Math.round(gen)}</div>
                        </div>
                      )
                    })}
                  </div>
                  <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 10 }}>
                    <span><span style={{ background: '#16a34a', display: 'inline-block', width: 12, height: 8, marginRight: 4 }} />Solar</span>
                    <span><span style={{ background: '#3b82f6', display: 'inline-block', width: 12, height: 8, marginRight: 4 }} />Wind</span>
                    <span><span style={{ background: '#ea580c', display: 'inline-block', width: 12, height: 8, marginRight: 4 }} />Generator (Diesel)</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'anomaly' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="ANOMALIES TODAY" value="2" icon="psychology" color="#d97706" sub="1 resolved, 1 monitoring" />
                  <KpiCard label="MODEL ACCURACY" value="97.3" unit="%" icon="verified" color="#16a34a" sub="30-day validation set" />
                  <KpiCard label="FALSE POSITIVE RATE" value="0.8" unit="%" icon="check_circle" color="#16a34a" sub="Last 30 days" />
                  <KpiCard label="SENSORS MONITORED" value={activeStation === 'maitri' ? 84 : 136} icon="sensors" color="#0b3b60" sub="Real-time ML inference" />
                </div>

                <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 14, letterSpacing: '0.05em' }}>ANOMALY DETECTION LOG — ISOLATION FOREST + LSTM AUTOENCODER</div>
                  {[{ id: 'ANM-2026-0847', time: '14:12 IST', sensor: 'Generator DG-2 Vibration (Z-axis)', value: '14.2 mm/s', baseline: '8.1 mm/s', deviation: '+75%', severity: 'HIGH', status: 'MONITORING', model: 'Isolation Forest' },{ id: 'ANM-2026-0846', time: '11:34 IST', sensor: 'Met Tower Wind Load Cell', value: '218 N', baseline: '145 N', deviation: '+50%', severity: 'MEDIUM', status: 'MONITORING', model: 'Statistical 3σ' },{ id: 'ANM-2026-0845', time: '08:21 IST', sensor: 'Fuel Line Pressure Sensor FP-3', value: '2.8 bar', baseline: '3.2 ± 0.15 bar', deviation: '-12.5%', severity: 'LOW', status: 'RESOLVED', model: 'LSTM' },{ id: 'ANM-2026-0844', time: 'Yesterday', sensor: 'Battery Bank Temp Cell-14', value: '48.2°C', baseline: '35 ± 5°C', deviation: '+21%', severity: 'MEDIUM', status: 'RESOLVED', model: 'Threshold' }].map(a => (
                    <div key={a.id} style={{ border: `1px solid ${a.status === 'MONITORING' ? '#fde68a' : '#e2e8f0'}`, padding: '12px', marginBottom: 8, background: a.status === 'MONITORING' ? '#fffbeb' : '#f8fafc' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <span style={{ fontWeight: 800, color: '#0b3b60', fontSize: 11 }}>{a.id}</span>
                          <span style={{ fontSize: 10, color: '#94a3b8' }}>{a.time}</span>
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <span style={{ fontSize: 10, fontWeight: 800, color: a.severity === 'HIGH' ? '#dc2626' : a.severity === 'MEDIUM' ? '#d97706' : '#16a34a', background: a.severity === 'HIGH' ? '#fef2f2' : a.severity === 'MEDIUM' ? '#fef3c7' : '#f0fdf4', padding: '1px 6px', border: `1px solid ${a.severity === 'HIGH' ? '#fecaca' : a.severity === 'MEDIUM' ? '#fde68a' : '#bbf7d0'}` }}>{a.severity}</span>
                          <span style={{ fontSize: 10, fontWeight: 800, color: a.status === 'MONITORING' ? '#d97706' : '#16a34a', background: a.status === 'MONITORING' ? '#fef3c7' : '#f0fdf4', padding: '1px 6px', border: `1px solid ${a.status === 'MONITORING' ? '#fde68a' : '#bbf7d0'}` }}>{a.status}</span>
                        </div>
                      </div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#1e293b', marginBottom: 4 }}>{a.sensor}</div>
                      <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#64748b' }}>
                        <span>Detected: <strong style={{ color: a.severity === 'HIGH' ? '#dc2626' : '#d97706' }}>{a.value}</strong></span>
                        <span>Baseline: <strong>{a.baseline}</strong></span>
                        <span>Deviation: <strong style={{ color: '#dc2626' }}>{a.deviation}</strong></span>
                        <span>Model: <strong style={{ color: '#7c3aed' }}>{a.model}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'maintenance' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="UPCOMING (7 DAYS)" value="3" icon="build" color="#d97706" sub="Scheduled maintenance" />
                  <KpiCard label="OVERDUE" value="0" icon="check_circle" color="#16a34a" sub="All current" />
                  <KpiCard label="AI RECOMMENDATIONS" value="5" icon="psychology" color="#7c3aed" sub="Predictive items" />
                  <KpiCard label="MTBF — DG-1" value="4,280" unit="hrs" icon="timer" color="#3b82f6" sub="Mean time between failures" />
                </div>

                <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 14, letterSpacing: '0.05em' }}>PREDICTIVE MAINTENANCE SCHEDULE — AI RECOMMENDATIONS</div>
                  {[{ id: 'PM-2026-114', asset: 'Generator DG-2', task: 'Vibration bearing inspection & lubrication', due: '2026-09-05', urgency: 'HIGH', trigger: 'Vibration anomaly ANM-0847 detected — bearing wear predicted', confidence: 91 },{ id: 'PM-2026-113', asset: 'VSAT Dish Actuator', task: 'Motor brushes replacement', due: '2026-09-10', urgency: 'MEDIUM', trigger: 'MTBF threshold: 2,100 hrs operational (recommended: 2,000)', confidence: 78 },{ id: 'PM-2026-112', asset: 'Fuel Transfer Pump FP-1', task: 'Seal kit replacement', due: '2026-09-14', urgency: 'MEDIUM', trigger: 'Periodic: 1,500 hr service interval', confidence: 85 },{ id: 'PM-2026-111', asset: 'Battery Bank — Cells 1-20', task: 'Capacity test & cell balancing', due: '2026-09-20', urgency: 'LOW', trigger: 'Quarterly capacity verification', confidence: 95 },{ id: 'PM-2026-110', asset: 'Wind Turbine WT-1', task: 'Blade inspection & pitch calibration', due: '2026-09-28', urgency: 'LOW', trigger: 'Annual inspection schedule', confidence: 99 }].map(m => (
                    <div key={m.id} style={{ border: `1px solid ${m.urgency === 'HIGH' ? '#fecaca' : m.urgency === 'MEDIUM' ? '#fde68a' : '#e2e8f0'}`, padding: '12px', marginBottom: 8, background: m.urgency === 'HIGH' ? '#fef2f2' : m.urgency === 'MEDIUM' ? '#fffbeb' : '#f8fafc' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <span style={{ fontWeight: 800, color: '#0b3b60', fontSize: 10 }}>{m.id}</span>
                          <span style={{ fontWeight: 700, color: '#1e293b', fontSize: 11 }}>{m.asset}</span>
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <span style={{ fontSize: 10, fontWeight: 800, color: m.urgency === 'HIGH' ? '#dc2626' : m.urgency === 'MEDIUM' ? '#d97706' : '#16a34a', background: 'rgba(255,255,255,0.7)', padding: '1px 6px', border: '1px solid currentColor' }}>{m.urgency}</span>
                          <span style={{ fontSize: 10, fontWeight: 700, color: '#475569' }}>Due: {m.due}</span>
                        </div>
                      </div>
                      <div style={{ fontSize: 11, color: '#1e293b', fontWeight: 600, marginBottom: 4 }}>{m.task}</div>
                      <div style={{ fontSize: 10, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#7c3aed' }}>psychology</span>
                        {m.trigger}
                        <span style={{ marginLeft: 'auto', fontWeight: 700, color: '#7c3aed' }}>AI Confidence: {m.confidence}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'expedition' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="CURRENT EXPEDITION" value="45th ISEA" icon="explore" color="#0b3b60" sub="Indian Scientific Expedition" />
                  <KpiCard label="CREW STRENGTH" value={activeStation === 'maitri' ? 24 : 32} unit="personnel" icon="group" color="#3b82f6" sub="All life-support nominal" />
                  <KpiCard label="MISSION DAYS LEFT" value="112" icon="calendar_month" color="#16a34a" sub="Winter campaign ends Feb 2027" />
                  <KpiCard label="CARGO CONSUMED" value="68" unit="%" icon="inventory" color="#ea580c" sub="Of expedition supplies" />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 14, letterSpacing: '0.05em' }}>EXPEDITION TIMELINE — 45TH ISEA</div>
                    {[{ phase: 'Pre-expedition Briefing', date: '2026-10-15', status: 'UPCOMING', color: '#64748b' },{ phase: 'Departure from Goa (MV Nuyina)', date: '2026-11-01', status: 'UPCOMING', color: '#64748b' },{ phase: 'Arrival at Bharati', date: '2026-12-15', status: 'PLANNED', color: '#3b82f6' },{ phase: 'Station Handover — Bharati', date: '2026-12-18', status: 'PLANNED', color: '#3b82f6' },{ phase: 'Arrival at Maitri', date: '2026-12-28', status: 'PLANNED', color: '#3b82f6' },{ phase: 'Return Departure', date: '2027-03-01', status: 'PLANNED', color: '#3b82f6' },{ phase: 'Arrival at Goa', date: '2027-04-10', status: 'PLANNED', color: '#3b82f6' }].map(e => (
                      <div key={e.phase} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', borderBottom: '1px solid #f1f5f9', fontSize: 11 }}>
                        <div style={{ width: 8, height: 8, background: e.color, borderRadius: '50%', flexShrink: 0 }} />
                        <div style={{ flex: 1 }}>
                          <span style={{ fontWeight: 700, color: '#1e293b' }}>{e.phase}</span>
                        </div>
                        <span style={{ color: '#64748b', whiteSpace: 'nowrap' }}>{e.date}</span>
                        <span style={{ fontSize: 9, fontWeight: 700, color: e.color, background: '#f8fafc', padding: '1px 5px', border: '1px solid #e2e8f0' }}>{e.status}</span>
                      </div>
                    ))}
                  </div>

                  <div style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 14, letterSpacing: '0.05em' }}>RESOURCE ADEQUACY FORECAST — AI MISSION PLANNER</div>
                    {[{ resource: 'Diesel Fuel (HSD)', current: `${(activeStation === 'maitri' ? 138400 : 210500).toLocaleString()} L`, adequacy: activeStation === 'maitri' ? 111 : 125, needed: 90, status: 'ADEQUATE' },{ resource: 'Aviation Fuel (ATF)', current: '28,400 L', adequacy: 95, needed: 60, status: 'ADEQUATE' },{ resource: 'LPG (Cooking)', current: '142 cylinders', adequacy: 180, needed: 90, status: 'SURPLUS' },{ resource: 'Medical Supplies', current: '100%', adequacy: 365, needed: 90, status: 'ADEQUATE' },{ resource: 'Emergency Rations', current: '72 person-days', adequacy: 72, needed: 30, status: 'ADEQUATE' }].map(r => (
                      <div key={r.resource} style={{ padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                          <span style={{ fontWeight: 700, color: '#1e293b' }}>{r.resource}</span>
                          <span style={{ fontSize: 10, fontWeight: 800, color: r.status === 'SURPLUS' ? '#0b3b60' : '#16a34a', background: r.status === 'SURPLUS' ? '#f0f9ff' : '#f0fdf4', padding: '1px 6px', border: `1px solid ${r.status === 'SURPLUS' ? '#bae6fd' : '#bbf7d0'}` }}>{r.status}</span>
                        </div>
                        <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#64748b', marginBottom: 4 }}>
                          <span>Current: <strong>{r.current}</strong></span>
                          <span>Covers: <strong style={{ color: '#16a34a' }}>{r.adequacy} days</strong></span>
                          <span>Required: <strong>{r.needed} days</strong></span>
                        </div>
                        <div style={{ height: 4, background: '#e2e8f0' }}>
                          <div style={{ height: '100%', width: `${Math.min(100, (r.needed / r.adequacy) * 100)}%`, background: '#16a34a' }} />
                        </div>
                      </div>
                    ))}
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
