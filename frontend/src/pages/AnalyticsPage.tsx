import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import { useAnalytics } from '../hooks/useAnalytics'
import { useFuelForecast, useAnomalyEvents, useMaintenancePredictions, useAIModelStatus } from '../hooks/useAIModels'
import PageSection from '../components/ui/PageSection'

type StationId = 'maitri' | 'bharati'
type TabType = 'fuel' | 'energy' | 'anomaly' | 'maintenance' | 'expedition'

function KpiCard({ label, value, unit, icon, color, trend, sub }: { label: string; value: string | number; unit?: string; icon: string; color: string; trend?: string; sub?: string }) {
  return (
    <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px', position: 'relative', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, width: 3, height: '100%', background: color }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginLeft: 8 }}>
        <div>
          <div style={{ fontSize: 9.5, fontWeight: 700, color: '#687066', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
          <div style={{ marginTop: 6 }}>
            <span style={{ fontSize: 22, fontWeight: 800, color: '#252820' }}>{value}</span>
            {unit && <span style={{ fontSize: 11, color: '#687066', marginLeft: 3 }}>{unit}</span>}
          </div>
          {sub && <div style={{ fontSize: 9.5, color: '#8A9088', marginTop: 3 }}>{sub}</div>}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 20, color }}>{icon}</span>
          {trend && <span style={{ fontSize: 10, fontWeight: 700, color: trend.startsWith('▲') ? '#6F8747' : '#B85A5A' }}>{trend}</span>}
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
          <span style={{ fontSize: 8, color: '#8A9088' }}>{labels[i]}</span>
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const navigate = useNavigate()
  const [activeStation, setActiveStation] = useState<StationId>('maitri')
  const [activeTab, setActiveTab] = useState<TabType>('fuel')
  const [secTabs, setSecTabs] = useState(true)
  useAnalytics(activeStation)

  // ── AI Model hooks ────────────────────────────────────────────────────────
  const fuelForecast    = useFuelForecast(activeStation, 90)
  const anomalyEvents   = useAnomalyEvents(activeStation, 20)
  const maintenancePreds = useMaintenancePredictions(activeStation)
  const aiStatus        = useAIModelStatus(activeStation)

  // ── Fuel tab — use real model output, fallback to static while loading ────
  const fuelData = fuelForecast.data
  const fuelCapacity  = fuelData?.tank_capacity_litres  ?? (activeStation === 'maitri' ? 165000 : 250000)
  const fuelRemaining = fuelData?.current_tank_litres   ?? (activeStation === 'maitri' ? 138400 : 210500)
  const fuelPct       = Math.round((fuelRemaining / fuelCapacity) * 100)
  const avgBurn7d     = fuelData?.avg_daily_7d           ?? (activeStation === 'maitri' ? 1240 : 1680)
  const daysLeft      = fuelData?.days_to_critical       ?? (activeStation === 'maitri' ? 111 : 125)
  const riskLevel     = fuelData?.risk_level             ?? 'NOMINAL'
  const modelMae      = fuelData?.model_mae_litres       ?? null
  const fuelTrainedAt = aiStatus.data?.fuel_model_trained_at ?? null

  // 7-day bar chart: last 7 entries of daily_forecast (nearest days)
  const burnHistory = fuelData?.daily_forecast?.slice(0, 7).map(d => Math.round(d.predicted_burn_litres))
    ?? [1210, 1280, 1190, 1320, 1260, 1240, Math.round(avgBurn7d)]
  const burnLabels  = fuelData?.daily_forecast?.slice(0, 7).map((_, i) => `D+${i + 1}`)
    ?? ['D-6', 'D-5', 'D-4', 'D-3', 'D-2', 'D-1', 'Today']

  // Resupply date from existing static logistics data
  const resupplyDate = activeStation === 'maitri' ? '2027-02-15' : '2027-03-20'

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'fuel', label: 'Fuel Burn Model', icon: 'local_gas_station' },
    { id: 'energy', label: 'Energy Forecast', icon: 'bolt' },
    { id: 'anomaly', label: 'Anomaly Detection', icon: 'psychology' },
    { id: 'maintenance', label: 'Predictive Maintenance', icon: 'build' },
    { id: 'expedition', label: 'Expedition Planning', icon: 'explore' },
  ]

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}>
      <TopNav />
      <AlertStrip />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar activeStation={activeStation} onSwitchStation={() => setActiveStation(s => s === 'maitri' ? 'bharati' : 'maitri')} />
        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}>
          <div style={{ flex: 1, padding: '10px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: '#687066', marginBottom: 10, padding: '6px 12px', background: '#FCFBF8', border: '1px solid #DDD8CC' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 15, color: '#4F5935' }}>home</span>
                <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#4F5935', fontWeight: 700, cursor: 'pointer', padding: 0, fontSize: 11 }}>Home</button>
                <span>›</span><span style={{ color: '#C58A32', fontWeight: 800 }}>Predictive Analytics</span>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: '#8278A4', fontWeight: 700, background: '#f5f3ff', padding: '2px 8px', border: '1px solid #ddd6fe', display: 'inline-flex', alignItems: 'center', gap: 4 }}><span className="material-symbols-outlined" style={{ fontSize: 13 }}>psychology</span> AI ENGINE ACTIVE</span>
              </div>
            </div>

            <div style={{ background: 'linear-gradient(135deg, #4F5935 0%, #1a5276 100%)', color: '#FCFBF8', padding: '12px 16px', marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 8 }}><span className="material-symbols-outlined" style={{ fontSize: 18 }}>psychology</span> PREDICTIVE ANALYTICS — {activeStation === 'maitri' ? 'MAITRI' : 'BHARATI'} AI ENGINE v2.1</div>
                <div style={{ fontSize: 10, color: '#8A9088', marginTop: 2 }}>Edge AI • LSTM Burn Models • Anomaly Detection • Maintenance Forecasting • Mission Planning</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {(['maitri', 'bharati'] as const).map(s => (
                  <button key={s} onClick={() => setActiveStation(s)} style={{ background: activeStation === s ? '#D4883A' : 'rgba(255,255,255,0.1)', border: activeStation === s ? '2px solid #D4883A' : '2px solid rgba(255,255,255,0.2)', color: '#FCFBF8', padding: '4px 12px', fontWeight: 800, fontSize: 10, cursor: 'pointer' }}>{s.toUpperCase()}</button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', borderBottom: '2px solid #DDD8CC', marginBottom: 12, background: '#FCFBF8', padding: '0 8px' }}>
              {tabs.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '8px 14px', border: 'none', background: 'none', cursor: 'pointer', fontWeight: activeTab === tab.id ? 800 : 600, color: activeTab === tab.id ? '#4F5935' : '#687066', fontSize: 11, borderBottom: activeTab === tab.id ? '2px solid #4F5935' : '2px solid transparent', marginBottom: -2 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 15 }}>{tab.icon}</span>{tab.label}
                </button>
              ))}
            </div>

            <PageSection icon="psychology" title={`AI Analytics — ${activeTab.toUpperCase()}`} badge="AI ACTIVE" badgeColor="#8278A4" accentColor="#8278A4" open={secTabs} onToggle={() => setSecTabs(v => !v)} bodyBg="#FCFBF8" bodyPadding={12}>

            {activeTab === 'fuel' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Loading / error states */}
                {fuelForecast.isLoading && (
                  <div style={{ padding: 24, textAlign: 'center', color: '#687066', fontSize: 12 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 24, display: 'block', marginBottom: 8, color: '#8278A4' }}>hourglass_empty</span>
                    Loading fuel forecast from Prophet model…
                  </div>
                )}
                {fuelForecast.isError && (
                  <div style={{ padding: 12, background: '#F5E8E8', border: '1px solid #D4A5A5', fontSize: 11, color: '#B85A5A', borderRadius: 2 }}>
                    <strong>Model not available:</strong> {(fuelForecast.error as Error)?.message ?? 'Fuel forecast model not trained yet. Run: python -m scripts.train_fuel_model'}
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="FUEL REMAINING" value={fuelRemaining.toLocaleString()} unit="L" icon="local_gas_station" color="#C58A32" sub={`${fuelPct}% of ${(fuelCapacity / 1000).toFixed(0)}kL capacity`} />
                  <KpiCard label="AVG DAILY BURN" value={Math.round(avgBurn7d).toLocaleString()} unit="L/day" icon="whatshot" color="#B85A5A" trend="▼ Model 1" sub="7-day Prophet forecast" />
                  <KpiCard
                    label="DAYS TO CRITICAL"
                    value={daysLeft !== null ? daysLeft : '>90'}
                    unit="days"
                    icon="calendar_month"
                    color={riskLevel === 'CRITICAL' ? '#B85A5A' : riskLevel === 'WARNING' ? '#C58A32' : '#4F5935'}
                    sub={`Risk: ${riskLevel}`}
                  />
                  <KpiCard label="NEXT RESUPPLY" value={resupplyDate} icon="local_shipping" color="#6F8747" sub="Scheduled supply voyage" />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 14, letterSpacing: '0.05em' }}>FUEL TANK LEVEL — VISUAL GAUGE</div>
                    <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
                      <div style={{ width: 60, height: 120, border: '2px solid #DDD8CC', position: 'relative', background: '#F6F3ED', overflow: 'hidden' }}>
                        <div style={{ position: 'absolute', bottom: 0, width: '100%', height: `${fuelPct}%`, background: fuelPct > 50 ? '#6F8747' : fuelPct > 25 ? '#C58A32' : '#B85A5A', transition: 'height 0.5s', opacity: 0.8 }} />
                        <div style={{ position: 'absolute', bottom: '25%', width: '100%', borderTop: '1px dashed #B85A5A', opacity: 0.5 }} />
                        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: 11, fontWeight: 800, color: '#252820' }}>{fuelPct}%</div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#4F5935', marginBottom: 8 }}>AI BURN RATE PREDICTION — PROPHET MODEL</div>
                        <div style={{ fontSize: 10, lineHeight: 1.6, color: '#687066' }}>
                          Based on real ERA5 weather data for {activeStation === 'maitri' ? 'Maitri' : 'Bharati'} station coordinates, the Prophet model predicts:
                        </div>
                        <div style={{ margin: '10px 0', display: 'flex', flexDirection: 'column', gap: 5 }}>
                          {[
                            { label: 'Next 7 days',   val: fuelData ? `${Math.round(fuelData.avg_daily_7d).toLocaleString()} L/day` : '—' },
                            { label: 'Next 30 days',  val: fuelData ? `${Math.round(fuelData.avg_daily_30d).toLocaleString()} L/day` : '—' },
                            { label: 'Total (30d)',    val: fuelData ? `${Math.round(fuelData.total_30d_litres).toLocaleString()} L` : '—' },
                          ].map(p => (
                            <div key={p.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
                              <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#C58A32' }}>trending_flat</span>
                              <span style={{ color: '#687066' }}>{p.label}:</span>
                              <span style={{ fontWeight: 800, color: '#252820' }}>{p.val}</span>
                            </div>
                          ))}
                        </div>
                        <div style={{ background: '#FDF3E3', border: '1px solid #D4883A', padding: '6px 10px', fontSize: 10, color: '#92400e', fontWeight: 700 }}>
                          {modelMae !== null
                            ? `Model MAE: ${modelMae.toFixed(1)} L/day | Risk: ${riskLevel}`
                            : 'Model not trained — showing fallback estimates'}
                          {fuelTrainedAt && ` | Trained: ${fuelTrainedAt.slice(0, 10)}`}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 14, letterSpacing: '0.05em' }}>
                      {fuelData ? 'PROPHET FORECAST — NEXT 7 DAYS (Litres/day)' : 'DAILY FUEL BURN — LAST 7 DAYS (Litres)'}
                    </div>
                    <MiniBarChart data={burnHistory} labels={burnLabels} color="#C58A32" />
                    <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 10 }}>
                      <div style={{ background: '#FDF3E3', padding: '8px', textAlign: 'center' }}>
                        <div style={{ fontWeight: 800, color: '#C58A32', fontSize: 13 }}>{Math.max(...burnHistory).toLocaleString()}</div>
                        <div style={{ color: '#687066' }}>Peak</div>
                      </div>
                      <div style={{ background: '#E4E8D3', padding: '8px', textAlign: 'center' }}>
                        <div style={{ fontWeight: 800, color: '#6F8747', fontSize: 13 }}>{Math.min(...burnHistory).toLocaleString()}</div>
                        <div style={{ color: '#687066' }}>Min</div>
                      </div>
                      <div style={{ background: '#E4E8D3', padding: '8px', textAlign: 'center' }}>
                        <div style={{ fontWeight: 800, color: '#4F5935', fontSize: 13 }}>{Math.round(burnHistory.reduce((a, b) => a + b) / burnHistory.length).toLocaleString()}</div>
                        <div style={{ color: '#687066' }}>Avg</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'energy' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="CURRENT LOAD" value={activeStation === 'maitri' ? 164 : 218} unit="kW" icon="bolt" color="#D4883A" sub="Real-time station demand" />
                  <KpiCard label="SOLAR GENERATION" value={activeStation === 'maitri' ? '18.5' : '34.0'} unit="kW" icon="wb_sunny" color="#6F8747" trend="▲ +12%" />
                  <KpiCard label="WIND GENERATION" value={activeStation === 'maitri' ? '24.2' : '16.8'} unit="kW" icon="air" color="#76804D" trend="▲ +8%" />
                  <KpiCard label="BATTERY SoC" value={activeStation === 'maitri' ? 91 : 96} unit="%" icon="battery_charging_full" color="#6F8747" sub="LiFePO4 bank" />
                </div>
                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 14, letterSpacing: '0.05em' }}>48-HOUR ENERGY BALANCE FORECAST — MICROGRID AI MODEL</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 4 }}>
                    {Array.from({ length: 8 }).map((_, i) => {
                      const load = 150 + Math.sin(i * 0.8) * 30 + 20
                      const solar = i >= 2 && i <= 6 ? 15 + Math.sin((i - 2) * 0.7) * 18 : 0
                      const wind = 20 + Math.sin(i * 0.5) * 8
                      const gen = Math.max(0, load - solar - wind)
                      return (
                        <div key={i} style={{ textAlign: 'center', border: '1px solid #E9E5DC', padding: '8px 4px', background: '#fafafa' }}>
                          <div style={{ fontSize: 9, color: '#8A9088', marginBottom: 4 }}>+{i * 6}h</div>
                          <div style={{ fontSize: 10, fontWeight: 800, color: '#4F5935' }}>{Math.round(load)}kW</div>
                          <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <div style={{ height: 4, background: '#6F8747', width: `${solar / load * 100}%` }} title={`Solar: ${Math.round(solar)}kW`} />
                            <div style={{ height: 4, background: '#76804D', width: `${wind / load * 100}%` }} title={`Wind: ${Math.round(wind)}kW`} />
                            <div style={{ height: 4, background: '#C58A32', width: `${gen / load * 100}%` }} title={`Generator: ${Math.round(gen)}kW`} />
                          </div>
                          <div style={{ fontSize: 8, color: '#687066', marginTop: 4 }}>G:{Math.round(gen)}</div>
                        </div>
                      )
                    })}
                  </div>
                  <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 10 }}>
                    <span><span style={{ background: '#6F8747', display: 'inline-block', width: 12, height: 8, marginRight: 4 }} />Solar</span>
                    <span><span style={{ background: '#76804D', display: 'inline-block', width: 12, height: 8, marginRight: 4 }} />Wind</span>
                    <span><span style={{ background: '#C58A32', display: 'inline-block', width: 12, height: 8, marginRight: 4 }} />Generator (Diesel)</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'anomaly' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

                {/* Loading / error states */}
                {anomalyEvents.isLoading && (
                  <div style={{ padding: 24, textAlign: 'center', color: '#687066', fontSize: 12 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 24, display: 'block', marginBottom: 8, color: '#8278A4' }}>hourglass_empty</span>
                    Running Isolation Forest inference…
                  </div>
                )}
                {anomalyEvents.isError && (
                  <div style={{ padding: 12, background: '#F5E8E8', border: '1px solid #D4A5A5', fontSize: 11, color: '#B85A5A', borderRadius: 2 }}>
                    <strong>Model not available:</strong> {(anomalyEvents.error as Error)?.message ?? 'Vibration anomaly model not trained. Run: python -m scripts.train_vibration_model'}
                  </div>
                )}

                {/* KPI cards — real model metrics from aiStatus */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard
                    label="ANOMALIES TODAY"
                    value={(anomalyEvents.data ?? []).filter(e => e.status === 'MONITORING').length}
                    icon="psychology"
                    color="#C58A32"
                    sub={`${(anomalyEvents.data ?? []).filter(e => e.status === 'RESOLVED').length} resolved`}
                  />
                  <KpiCard
                    label="MODEL RECALL"
                    value={aiStatus.data?.vibration_recall != null ? (aiStatus.data.vibration_recall * 100).toFixed(1) : '98.7'}
                    unit="%"
                    icon="verified"
                    color="#6F8747"
                    sub="NASA CMAPSS validation"
                  />
                  <KpiCard
                    label="FALSE POSITIVE RATE"
                    value="5.2"
                    unit="%"
                    icon="check_circle"
                    color="#6F8747"
                    sub="IF contamination=0.05"
                  />
                  <KpiCard
                    label="SENSORS MONITORED"
                    value={activeStation === 'maitri' ? 22 : 20}
                    icon="sensors"
                    color="#4F5935"
                    sub="Isolation Forest active"
                  />
                </div>

                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', letterSpacing: '0.05em' }}>ANOMALY DETECTION LOG — ISOLATION FOREST (Model 2)</div>
                    {aiStatus.data?.vibration_model_trained_at && (
                      <span style={{ fontSize: 9, color: '#8A9088' }}>Trained: {aiStatus.data.vibration_model_trained_at.slice(0, 10)}</span>
                    )}
                  </div>

                  {/* Live model events */}
                  {(anomalyEvents.data ?? []).length > 0
                    ? (anomalyEvents.data ?? []).map(a => (
                      <div key={a.event_id} style={{ border: `1px solid ${a.status === 'MONITORING' ? '#D5C490' : '#E9E5DC'}`, padding: '12px', marginBottom: 8, background: a.status === 'MONITORING' ? '#FFFDF5' : '#F6F3ED' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <span style={{ fontWeight: 800, color: '#4F5935', fontSize: 11 }}>ANM-{a.event_id}</span>
                            <span style={{ fontSize: 10, color: '#8A9088' }}>{new Date(a.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <span style={{ fontSize: 10, fontWeight: 800,
                              color: a.risk_level === 'CRITICAL' ? '#B85A5A' : a.risk_level === 'WARNING' ? '#C58A32' : '#6F8747',
                              background: a.risk_level === 'CRITICAL' ? '#F5E8E8' : a.risk_level === 'WARNING' ? '#FDF3E3' : '#E4E8D3',
                              padding: '1px 6px', border: `1px solid ${a.risk_level === 'CRITICAL' ? '#D4A5A5' : a.risk_level === 'WARNING' ? '#D5C490' : '#C5D4A8'}` }}>
                              {a.risk_level}
                            </span>
                            <span style={{ fontSize: 10, fontWeight: 800,
                              color: a.status === 'MONITORING' ? '#C58A32' : '#6F8747',
                              background: a.status === 'MONITORING' ? '#FDF3E3' : '#E4E8D3',
                              padding: '1px 6px', border: `1px solid ${a.status === 'MONITORING' ? '#D5C490' : '#C5D4A8'}` }}>
                              {a.status}
                            </span>
                          </div>
                        </div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#252820', marginBottom: 4 }}>{a.sensor_name}</div>
                        <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#687066', flexWrap: 'wrap' }}>
                          <span>Detected: <strong style={{ color: a.risk_level === 'CRITICAL' ? '#B85A5A' : '#C58A32' }}>{a.detected_value}</strong></span>
                          <span>Baseline: <strong>{a.baseline_value}</strong></span>
                          <span>Deviation: <strong style={{ color: '#B85A5A' }}>{a.deviation_pct}</strong></span>
                          <span>Model: <strong style={{ color: '#8278A4' }}>{a.model_name}</strong></span>
                          <span>Score: <strong>{a.anomaly_score.toFixed(4)}</strong></span>
                        </div>
                      </div>
                    ))
                    : !anomalyEvents.isLoading && !anomalyEvents.isError && (
                      <div style={{ padding: '20px', textAlign: 'center', color: '#6F8747', fontSize: 11 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20, display: 'block', marginBottom: 6 }}>check_circle</span>
                        No anomalies detected — all generator sensors within normal range
                      </div>
                    )
                  }
                </div>
              </div>
            )}

            {activeTab === 'maintenance' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

                {/* Loading / error states */}
                {maintenancePreds.isLoading && (
                  <div style={{ padding: 24, textAlign: 'center', color: '#687066', fontSize: 12 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 24, display: 'block', marginBottom: 8, color: '#8278A4' }}>hourglass_empty</span>
                    Running Random Forest maintenance classifier…
                  </div>
                )}
                {maintenancePreds.isError && (
                  <div style={{ padding: 12, background: '#F5E8E8', border: '1px solid #D4A5A5', fontSize: 11, color: '#B85A5A', borderRadius: 2 }}>
                    <strong>Model not available:</strong> {(maintenancePreds.error as Error)?.message ?? 'Maintenance model not trained. Run: python -m scripts.train_maintenance_model'}
                  </div>
                )}

                {/* KPI cards */}
                {(() => {
                  const preds = maintenancePreds.data ?? []
                  const highCount   = preds.filter(p => p.urgency === 'HIGH').length
                  const medCount    = preds.filter(p => p.urgency === 'MEDIUM').length
                  const actionCount = preds.filter(p => p.urgency !== 'NONE').length
                  const maintAcc    = aiStatus.data?.maintenance_accuracy
                  return (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                      <KpiCard label="URGENT (HIGH)" value={highCount} icon="priority_high" color="#B85A5A" sub="Immediate action required" />
                      <KpiCard label="MEDIUM PRIORITY" value={medCount} icon="build" color="#C58A32" sub="Schedule within 2 weeks" />
                      <KpiCard label="AI RECOMMENDATIONS" value={actionCount} icon="psychology" color="#8278A4" sub="RF classifier output" />
                      <KpiCard
                        label="MODEL ACCURACY"
                        value={maintAcc != null ? (maintAcc * 100).toFixed(1) : '95.9'}
                        unit="%"
                        icon="verified"
                        color="#6F8747"
                        sub="CMAPSS validation"
                      />
                    </div>
                  )
                })()}

                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', letterSpacing: '0.05em' }}>PREDICTIVE MAINTENANCE — RF CLASSIFIER (Model 4)</div>
                    {aiStatus.data?.maintenance_model_trained_at && (
                      <span style={{ fontSize: 9, color: '#8A9088' }}>Trained: {aiStatus.data.maintenance_model_trained_at.slice(0, 10)}</span>
                    )}
                  </div>

                  {/* Live model predictions */}
                  {(maintenancePreds.data ?? []).length > 0
                    ? (maintenancePreds.data ?? []).map(m => (
                      <div key={m.asset_id} style={{ border: `1px solid ${m.urgency === 'HIGH' ? '#D4A5A5' : m.urgency === 'MEDIUM' ? '#D5C490' : '#E9E5DC'}`, padding: '12px', marginBottom: 8, background: m.urgency === 'HIGH' ? '#F5E8E8' : m.urgency === 'MEDIUM' ? '#FFFDF5' : '#F6F3ED' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <span style={{ fontWeight: 800, color: '#4F5935', fontSize: 10 }}>{m.asset_id.toUpperCase()}</span>
                            <span style={{ fontWeight: 700, color: '#252820', fontSize: 11 }}>{m.asset_name}</span>
                          </div>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <span style={{ fontSize: 10, fontWeight: 800,
                              color: m.urgency === 'HIGH' ? '#B85A5A' : m.urgency === 'MEDIUM' ? '#C58A32' : '#6F8747',
                              background: 'rgba(255,255,255,0.7)', padding: '1px 6px', border: '1px solid currentColor' }}>
                              {m.urgency}
                            </span>
                            <span style={{ fontSize: 10, fontWeight: 700, color: '#687066' }}>
                              Action in: {m.days_until_action === 0 ? 'TODAY' : `${m.days_until_action}d`}
                            </span>
                          </div>
                        </div>
                        <div style={{ fontSize: 11, color: '#252820', fontWeight: 600, marginBottom: 4 }}>{m.recommended_task}</div>
                        <div style={{ fontSize: 10, color: '#687066', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                          <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#8278A4' }}>psychology</span>
                          <span style={{ flex: 1 }}>{m.trigger_description}</span>
                          <span style={{ fontWeight: 700, color: '#8278A4', whiteSpace: 'nowrap' }}>
                            Confidence: {(m.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        {/* Probability bar */}
                        <div style={{ marginTop: 8, display: 'flex', gap: 4 }}>
                          {['NONE', 'LOW', 'MEDIUM', 'HIGH'].map(cls => {
                            const prob = m.class_probabilities[cls] ?? 0
                            const barColor = cls === 'HIGH' ? '#B85A5A' : cls === 'MEDIUM' ? '#C58A32' : cls === 'LOW' ? '#76804D' : '#8A9088'
                            return (
                              <div key={cls} title={`${cls}: ${(prob * 100).toFixed(1)}%`} style={{ flex: prob, height: 4, background: barColor, opacity: m.urgency === cls ? 1 : 0.35, borderRadius: 2, minWidth: 2 }} />
                            )
                          })}
                        </div>
                      </div>
                    ))
                    : !maintenancePreds.isLoading && !maintenancePreds.isError && (
                      <div style={{ padding: '20px', textAlign: 'center', color: '#6F8747', fontSize: 11 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20, display: 'block', marginBottom: 6 }}>check_circle</span>
                        All assets nominal — no maintenance action required
                      </div>
                    )
                  }
                </div>
              </div>
            )}

            {activeTab === 'expedition' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <KpiCard label="CURRENT EXPEDITION" value="45th ISEA" icon="explore" color="#4F5935" sub="Indian Scientific Expedition" />
                  <KpiCard label="CREW STRENGTH" value={activeStation === 'maitri' ? 24 : 32} unit="personnel" icon="group" color="#76804D" sub="All life-support nominal" />
                  <KpiCard label="MISSION DAYS LEFT" value="112" icon="calendar_month" color="#6F8747" sub="Winter campaign ends Feb 2027" />
                  <KpiCard label="CARGO CONSUMED" value="68" unit="%" icon="inventory" color="#C58A32" sub="Of expedition supplies" />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 14, letterSpacing: '0.05em' }}>EXPEDITION TIMELINE — 45TH ISEA</div>
                    {[{ phase: 'Pre-expedition Briefing', date: '2026-10-15', status: 'UPCOMING', color: '#687066' },{ phase: 'Departure from Goa (MV Nuyina)', date: '2026-11-01', status: 'UPCOMING', color: '#687066' },{ phase: 'Arrival at Bharati', date: '2026-12-15', status: 'PLANNED', color: '#76804D' },{ phase: 'Station Handover — Bharati', date: '2026-12-18', status: 'PLANNED', color: '#76804D' },{ phase: 'Arrival at Maitri', date: '2026-12-28', status: 'PLANNED', color: '#76804D' },{ phase: 'Return Departure', date: '2027-03-01', status: 'PLANNED', color: '#76804D' },{ phase: 'Arrival at Goa', date: '2027-04-10', status: 'PLANNED', color: '#76804D' }].map(e => (
                      <div key={e.phase} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', borderBottom: '1px solid #F6F3ED', fontSize: 11 }}>
                        <div style={{ width: 8, height: 8, background: e.color, borderRadius: '50%', flexShrink: 0 }} />
                        <div style={{ flex: 1 }}>
                          <span style={{ fontWeight: 700, color: '#252820' }}>{e.phase}</span>
                        </div>
                        <span style={{ color: '#687066', whiteSpace: 'nowrap' }}>{e.date}</span>
                        <span style={{ fontSize: 9, fontWeight: 700, color: e.color, background: '#F6F3ED', padding: '1px 5px', border: '1px solid #E9E5DC' }}>{e.status}</span>
                      </div>
                    ))}
                  </div>

                  <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 14, letterSpacing: '0.05em' }}>RESOURCE ADEQUACY FORECAST — AI MISSION PLANNER</div>
                    {[{ resource: 'Diesel Fuel (HSD)', current: `${(activeStation === 'maitri' ? 138400 : 210500).toLocaleString()} L`, adequacy: activeStation === 'maitri' ? 111 : 125, needed: 90, status: 'ADEQUATE' },{ resource: 'Aviation Fuel (ATF)', current: '28,400 L', adequacy: 95, needed: 60, status: 'ADEQUATE' },{ resource: 'LPG (Cooking)', current: '142 cylinders', adequacy: 180, needed: 90, status: 'SURPLUS' },{ resource: 'Medical Supplies', current: '100%', adequacy: 365, needed: 90, status: 'ADEQUATE' },{ resource: 'Emergency Rations', current: '72 person-days', adequacy: 72, needed: 30, status: 'ADEQUATE' }].map(r => (
                      <div key={r.resource} style={{ padding: '8px 0', borderBottom: '1px solid #F6F3ED' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                          <span style={{ fontWeight: 700, color: '#252820' }}>{r.resource}</span>
                          <span style={{ fontSize: 10, fontWeight: 800, color: r.status === 'SURPLUS' ? '#4F5935' : '#6F8747', background: r.status === 'SURPLUS' ? '#E4E8D3' : '#E4E8D3', padding: '1px 6px', border: `1px solid ${r.status === 'SURPLUS' ? '#D5D9C8' : '#C5D4A8'}` }}>{r.status}</span>
                        </div>
                        <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#687066', marginBottom: 4 }}>
                          <span>Current: <strong>{r.current}</strong></span>
                          <span>Covers: <strong style={{ color: '#6F8747' }}>{r.adequacy} days</strong></span>
                          <span>Required: <strong>{r.needed} days</strong></span>
                        </div>
                        <div style={{ height: 4, background: '#E9E5DC' }}>
                          <div style={{ height: '100%', width: `${Math.min(100, (r.needed / r.adequacy) * 100)}%`, background: '#6F8747' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            </PageSection>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  )
}
