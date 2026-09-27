import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import { useLanguage } from '../context/LanguageContext'
import { useSensors } from '../hooks/useSensors'
import { useInventory } from '../hooks/useInventory'

export default function EnergyPage() {
  const navigate = useNavigate()
  const { t, lang } = useLanguage()

  const [activeStation, setActiveStation] = useState<'maitri' | 'bharati'>('maitri')
  const [activeTab, setActiveTab] = useState<'overview' | 'generators' | 'fuel' | 'microgrid' | 'prediction'>('overview')

  // Interactive Simulation Controls
  const [ambientTemp, setAmbientTemp] = useState<number>(-28)
  const [crewOccupancy, setCrewOccupancy] = useState<number>(24)
  const [selectedGen, setSelectedGen] = useState<number>(1)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  // Real-Time Generator Telemetry & Preventive Maintenance States
  const [activeTelemetryGen, setActiveTelemetryGen] = useState<number>(1)
  const [isDiagnosticScanning, setIsDiagnosticScanning] = useState<boolean>(false)
  const [diagnosticReport, setDiagnosticReport] = useState<string | null>(null)

  // ── Live sensor + inventory data from Neon ────────────────────────────────
  const { data: energySensors } = useSensors(activeStation, 'energy')
  const { data: inventoryItems } = useInventory(activeStation, 'FUEL')

  /** Find latest sensor value by keyword in sensor_id */
  function sv(keyword: string): number | null {
    return energySensors?.find(s => s.sensor_id.toLowerCase().includes(keyword))?.latest_value ?? null
  }

  // Live derived values (fall back to simulation defaults if DB returns null)
  const liveKwOutput = sv('kw_output') ?? sv('kw') ?? null
  const liveFuelPct  = sv('fuel_pct') ?? sv('fuel') ?? null
  const liveSolar    = sv('solar') ?? null

  // Fuel from inventory_items (first FUEL item by name containing 'diesel' or 'generator')
  const dieselItem = inventoryItems?.find(i =>
    i.name.toLowerCase().includes('diesel') || i.name.toLowerCase().includes('generator')
  )
  const fuelRemainingLitres = dieselItem?.quantity ?? (activeStation === 'maitri' ? 138400 : 210500)
  const totalCapacityLitres = activeStation === 'maitri' ? 165000 : 250000
  const fuelPct = liveFuelPct !== null ? liveFuelPct : Math.round((fuelRemainingLitres / totalCapacityLitres) * 100)

  // Simulation-derived values (used for sliders / prediction tab)
  const baseLoad = liveKwOutput ?? (activeStation === 'maitri' ? 142 : 185)
  const tempFactor = Math.max(0, (-ambientTemp - 15) * 1.8)
  const occupancyFactor = (crewOccupancy - 20) * 1.2
  const currentTotalLoad = Math.round(baseLoad + tempFactor + occupancyFactor)

  const solarGen = liveSolar ?? (ambientTemp > -35 ? (activeStation === 'maitri' ? 18.5 : 34.0) : 0)
  const windGen = activeStation === 'maitri' ? 24.2 : 16.8
  const batterySoC = activeStation === 'maitri' ? 91 : 96
  const genOutput = Math.max(0, currentTotalLoad - solarGen - windGen)

  const hourlyBurnLitres = (genOutput * 0.28).toFixed(1)
  const dailyBurnLitres = Math.round(parseFloat(hourlyBurnLitres) * 24)
  const daysOfAutonomy = Math.round(fuelRemainingLitres / (dailyBurnLitres || 1))

  function runEngineDiagnostic() {
    setIsDiagnosticScanning(true)
    setDiagnosticReport(null)
    setTimeout(() => {
      setIsDiagnosticScanning(false)
      setDiagnosticReport(`✅ All sensors normal. Engine running smooth. Next service in 184 hrs.`)
    }, 1000)
  }

  function triggerGenAction(genId: number, action: string) {
    setActionMessage(`[${new Date().toLocaleTimeString('en-GB')}] ⚙️ Dispatch Command: Generator DG-${genId} -> ${action.toUpperCase()} signal transmitted to station microgrid PLC.`)
    setTimeout(() => setActionMessage(null), 5000)
  }



  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
      <TopNav />
      <AlertStrip />

      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar activeStation={activeStation} onSwitchStation={() => setActiveStation(s => s === 'maitri' ? 'bharati' : 'maitri')} />

        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
          <div style={{ flex: 1, padding: '10px 14px' }}>
            {/* Breadcrumb Navigation */}
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
                <span style={{ color: '#ea580c', fontWeight: 800 }}>
                  {lang === 'hi' ? 'ऊर्जा एवं हाइब्रिड माइक्रोग्रिड प्रबंधन' : 'Energy Systems & Polar Microgrid Command'}
                </span>
              </div>

              {/* Station Switcher Pills */}
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  onClick={() => setActiveStation('maitri')}
                  style={{
                    background: activeStation === 'maitri' ? '#0b3b60' : '#ffffff',
                    color: activeStation === 'maitri' ? '#ffffff' : '#0b3b60',
                    border: '1px solid #0b3b60',
                    padding: '4px 14px',
                    fontSize: 11,
                    fontWeight: 800,
                    cursor: 'pointer',
                    borderRadius: 3,
                  }}
                >
                  {lang === 'hi' ? 'मैत्री' : 'Maitri'}
                </button>
                <button
                  onClick={() => setActiveStation('bharati')}
                  style={{
                    background: activeStation === 'bharati' ? '#0b3b60' : '#ffffff',
                    color: activeStation === 'bharati' ? '#ffffff' : '#0b3b60',
                    border: '1px solid #0b3b60',
                    padding: '4px 14px',
                    fontSize: 11,
                    fontWeight: 800,
                    cursor: 'pointer',
                    borderRadius: 3,
                  }}
                >
                  {lang === 'hi' ? 'भारती' : 'Bharati'}
                </button>
              </div>
            </div>

            {/* Action Feedback Banner */}
            {actionMessage && (
              <div
                style={{
                  background: '#f0fdf4',
                  border: '1px solid #86efac',
                  color: '#166534',
                  padding: '6px 12px',
                  fontSize: 11,
                  fontWeight: 700,
                  marginBottom: 10,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>check_circle</span>
                <span>{actionMessage}</span>
              </div>
            )}

            {/* Top Microgrid KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10, marginBottom: 12 }}>
              {/* KPI 1: Active Station Load */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #0b3b60', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b', textTransform: 'uppercase' }}>
                    {lang === 'hi' ? 'कुल बिजली की खपत' : 'ELECTRICITY BEING USED'}
                  </span>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#0b3b60' }}>bolt</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                  <span style={{ fontSize: 22, fontWeight: 900, color: '#0b3b60' }}>{currentTotalLoad}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b' }}>kW (out of 300 kW Max)</span>
                </div>
                <div style={{ fontSize: 10, color: '#0284c7', fontWeight: 700, marginTop: 4 }}>
                  Total Station Power Used: {Math.round((currentTotalLoad / 300) * 100)}%
                </div>
              </div>

              {/* KPI 2: Generation Mix */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #16a34a', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b', textTransform: 'uppercase' }}>
                    {lang === 'hi' ? 'प्राकृतिक स्वच्छ बिजली' : 'CLEAN GREEN POWER'}
                  </span>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#16a34a' }}>eco</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                  <span style={{ fontSize: 22, fontWeight: 900, color: '#16a34a' }}>{(solarGen + windGen).toFixed(1)}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b' }}>kW from Nature</span>
                </div>
                <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginTop: 4 }}>
                  ☀️ Sun Panels: {solarGen} kW • 💨 Wind Turbines: {windGen} kW
                </div>
              </div>

              {/* KPI 3: Fuel Reserves & Autonomy */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #ea580c', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b', textTransform: 'uppercase' }}>
                    {lang === 'hi' ? 'डीजल ईंधन व शेष दिन' : 'DIESEL FUEL & DAYS LEFT'}
                  </span>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#ea580c' }}>local_gas_station</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                  <span style={{ fontSize: 22, fontWeight: 900, color: '#0f172a' }}>{daysOfAutonomy}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#ea580c' }}>Days of Fuel Left</span>
                </div>
                <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginTop: 4 }}>
                  In Tanks: <strong>{(fuelRemainingLitres / 1000).toFixed(1)}k Litres</strong> ({fuelPct}% Full) • Uses: <strong>{hourlyBurnLitres} L/hr</strong>
                </div>
              </div>

              {/* KPI 4: Power Quality & Grid Health */}
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #0284c7', padding: '10px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 800, color: '#64748b', textTransform: 'uppercase' }}>
                    {lang === 'hi' ? 'बिजली वोल्टेज व स्थिरता' : 'POWER VOLTAGE & STABILITY'}
                  </span>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#0284c7' }}>electrical_services</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                  <span style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>50.0 Hz</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#16a34a' }}>230V / 415V</span>
                </div>
                <div style={{ fontSize: 10, color: '#16a34a', fontWeight: 700, marginTop: 4 }}>
                  Electricity is Stable & Safe (Standard Indian Voltage)
                </div>
              </div>
            </div>

            {/* Sub-Navigation Tabs */}
            <div style={{ display: 'flex', gap: 4, borderBottom: '2px solid #cbd5e1', marginBottom: 12, background: '#ffffff', padding: '4px 8px 0 8px' }}>
              {[
                { id: 'overview', label: lang === 'hi' ? '⚡ जनरेटर स्वास्थ्य व बिजली सारांश' : '⚡ Generator Health & Power Overview', icon: 'speed' },
                { id: 'generators', label: lang === 'hi' ? '⚙️ सभी 4 जनरेटर (DG 1-4)' : '⚙️ All 4 Generators (DG 1-4)', icon: 'manufacturing' },
                { id: 'fuel', label: lang === 'hi' ? '🛢️ ईंधन टैंक व स्टोरेज' : '🛢️ Fuel Tanks & Storage', icon: 'propane_tank' },
                { id: 'prediction', label: lang === 'hi' ? '⛽ ईंधन कैलकुलेटर (Fuel Predictor)' : '⛽ Fuel Predictor', icon: 'psychology' },
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

            {/* ═══════════ TAB 1: MICROGRID FLOW & TELEMETRY ═══════════ */}
            {activeTab === 'overview' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 12 }}>
                {/* Real-time Generator Health & Preventive Maintenance Telemetry */}
                <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderTop: '3px solid #0b3b60', padding: 14, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                  {/* Header with Switcher */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 12, borderBottom: '1px solid #e2e8f0', paddingBottom: 8 }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#0b3b60' }}>speed</span>
                        <h3 style={{ fontSize: 13, fontWeight: 900, color: '#0b3b60', margin: 0 }}>
                          {activeStation.toUpperCase()} GENERATOR HEALTH & LIVE SENSORS
                        </h3>
                      </div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>
                        Live sensor stream from base generator
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {/* Active Genset Selector */}
                      <div style={{ display: 'flex', gap: 4, background: '#f1f5f9', padding: 2, borderRadius: 3 }}>
                        {[
                          { id: 1, label: 'Gen 1 (Active)' },
                          { id: 2, label: 'Gen 2 (Standby)' },
                          { id: 3, label: 'Gen 3 (Backup)' },
                        ].map((g) => (
                          <button
                            key={g.id}
                            onClick={() => { setActiveTelemetryGen(g.id); setDiagnosticReport(null); }}
                            style={{
                              background: activeTelemetryGen === g.id ? '#0b3b60' : 'transparent',
                              color: activeTelemetryGen === g.id ? '#ffffff' : '#334155',
                              border: 'none',
                              padding: '4px 8px',
                              fontSize: 10.5,
                              fontWeight: activeTelemetryGen === g.id ? 800 : 600,
                              cursor: 'pointer',
                              borderRadius: 2,
                            }}
                          >
                            {g.label}
                          </button>
                        ))}
                      </div>

                      <span style={{ fontSize: 10, fontWeight: 800, color: '#166534', background: '#dcfce7', border: '1px solid #86efac', padding: '3px 8px', borderRadius: 2 }}>
                        ● 98% Good
                      </span>
                    </div>
                  </div>

                  {/* 4 Clean Telemetry Cards */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10, marginBottom: 12 }}>
                    {/* Gauge 1: Vibration */}
                    <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderLeft: '4px solid #0284c7', padding: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>
                          📳 Vibration
                        </span>
                        <span style={{ fontSize: 9, fontWeight: 800, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 2 }}>
                          Smooth
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '2px 0' }}>
                        <span style={{ fontSize: 22, fontWeight: 900, color: '#0284c7' }}>
                          {activeTelemetryGen === 1 ? '1.82' : activeTelemetryGen === 2 ? '0.24' : '0.05'}
                        </span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>mm/s</span>
                      </div>
                      
                      {/* Live Waveform SVG */}
                      <div style={{ width: '100%', height: 24, background: '#e2e8f0', borderRadius: 2, overflow: 'hidden', margin: '4px 0' }}>
                        <svg viewBox="0 0 200 24" style={{ width: '100%', height: '100%' }}>
                          <path
                            d={activeTelemetryGen === 1 
                              ? "M0,12 Q10,3 20,12 T40,12 T60,12 T80,12 T100,12 T120,12 T140,12 T160,12 T180,12 T200,12"
                              : "M0,12 L200,12"}
                            fill="none"
                            stroke="#0284c7"
                            strokeWidth="1.8"
                          />
                        </svg>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: '#64748b' }}>
                        <span>Bearings: <strong>Good</strong></span>
                        <span>Limit: <strong>&lt; 4.5</strong></span>
                      </div>
                    </div>

                    {/* Gauge 2: Coolant Temp */}
                    <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderLeft: '4px solid #16a34a', padding: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>
                          🌡️ Coolant Temp
                        </span>
                        <span style={{ fontSize: 9, fontWeight: 800, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 2 }}>
                          Normal
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '2px 0' }}>
                        <span style={{ fontSize: 22, fontWeight: 900, color: '#16a34a' }}>
                          {activeTelemetryGen === 1 ? '82.4' : activeTelemetryGen === 2 ? '58.0' : '34.2'}
                        </span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>°C</span>
                      </div>

                      {/* Bar */}
                      <div style={{ width: '100%', height: 6, background: '#cbd5e1', borderRadius: 3, margin: '8px 0', overflow: 'hidden' }}>
                        <div
                          style={{
                            width: activeTelemetryGen === 1 ? '78%' : activeTelemetryGen === 2 ? '45%' : '20%',
                            height: '100%',
                            background: activeTelemetryGen === 1 ? '#16a34a' : '#0284c7',
                            transition: 'width 0.3s ease',
                          }}
                        />
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: '#64748b' }}>
                        <span>Flow: <strong>Normal</strong></span>
                        <span>Safe: <strong>80–88°C</strong></span>
                      </div>
                    </div>

                    {/* Gauge 3: Oil Pressure */}
                    <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderLeft: '4px solid #d97706', padding: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>
                          🛢️ Oil Pressure
                        </span>
                        <span style={{ fontSize: 9, fontWeight: 800, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 2 }}>
                          Good
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '2px 0' }}>
                        <span style={{ fontSize: 22, fontWeight: 900, color: '#d97706' }}>
                          {activeTelemetryGen === 1 ? '4.65' : '0.00'}
                        </span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>bar</span>
                      </div>

                      {/* Bar */}
                      <div style={{ width: '100%', height: 6, background: '#cbd5e1', borderRadius: 3, margin: '8px 0', overflow: 'hidden' }}>
                        <div
                          style={{
                            width: activeTelemetryGen === 1 ? '72%' : '0%',
                            height: '100%',
                            background: '#d97706',
                            transition: 'width 0.3s ease',
                          }}
                        />
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: '#64748b' }}>
                        <span>Filter: <strong>Clean</strong></span>
                        <span>Min: <strong>2.2 bar</strong></span>
                      </div>
                    </div>

                    {/* Gauge 4: Exhaust Temp */}
                    <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderLeft: '4px solid #7c3aed', padding: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: '#0b3b60' }}>
                          🔥 Exhaust Temp
                        </span>
                        <span style={{ fontSize: 9, fontWeight: 800, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 2 }}>
                          Balanced
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '2px 0' }}>
                        <span style={{ fontSize: 22, fontWeight: 900, color: '#7c3aed' }}>
                          {activeTelemetryGen === 1 ? '418' : activeTelemetryGen === 2 ? '42' : '18'}
                        </span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>°C</span>
                      </div>

                      {/* Mini Bars */}
                      <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 16, margin: '6px 0' }}>
                        {[414, 422, 418, 425, 416, 419].map((val, idx) => (
                          <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <div
                              style={{
                                width: '100%',
                                height: activeTelemetryGen === 1 ? `${(val / 500) * 16}px` : '2px',
                                background: '#7c3aed',
                                borderRadius: 1,
                              }}
                              title={`Cyl ${idx + 1}: ${activeTelemetryGen === 1 ? val : 25}°C`}
                            />
                          </div>
                        ))}
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: '#64748b' }}>
                        <span>6 Cylinders: <strong>Even</strong></span>
                        <span>Turbo: <strong>462°C</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* AI Health & Maintenance */}
                  <div style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '8px 12px', borderRadius: 3 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 6 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#0b3b60' }}>psychology</span>
                        <strong style={{ fontSize: 11, color: '#0b3b60' }}>
                          AI HEALTH & MAINTENANCE
                        </strong>
                      </div>

                      <div style={{ display: 'flex', gap: 6 }}>
                        <button
                          onClick={runEngineDiagnostic}
                          disabled={isDiagnosticScanning}
                          style={{
                            background: '#0b3b60',
                            color: '#ffffff',
                            border: 'none',
                            padding: '4px 8px',
                            fontSize: 10,
                            fontWeight: 800,
                            cursor: isDiagnosticScanning ? 'wait' : 'pointer',
                            borderRadius: 2,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: 13 }}>
                            {isDiagnosticScanning ? 'sync' : 'analytics'}
                          </span>
                          <span>{isDiagnosticScanning ? 'Checking...' : 'Run AI Check'}</span>
                        </button>

                        <button
                          onClick={() => alert(`Official Engine Health Audit Log: REF-NCPOR-GEN-DG0${activeTelemetryGen}-2026.pdf exported.`)}
                          style={{
                            background: '#ffffff',
                            color: '#0b3b60',
                            border: '1px solid #0b3b60',
                            padding: '4px 8px',
                            fontSize: 10,
                            fontWeight: 700,
                            cursor: 'pointer',
                            borderRadius: 2,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: 13 }}>picture_as_pdf</span>
                          <span>Export PDF</span>
                        </button>
                      </div>
                    </div>

                    {/* Output Banner */}
                    {diagnosticReport && (
                      <div style={{ background: '#ecfdf5', border: '1px solid #6ee7b7', color: '#065f46', padding: '4px 8px', fontSize: 10, fontWeight: 700, marginBottom: 6, borderRadius: 2 }}>
                        {diagnosticReport}
                      </div>
                    )}

                    {/* 4 Minimal Tiles */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 6, fontSize: 10 }}>
                      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: 6 }}>
                        <div style={{ color: '#64748b', fontSize: 9 }}>Life to Overhaul</div>
                        <div style={{ fontWeight: 900, color: '#0b3b60', fontSize: 11.5 }}>3,840 Hrs (160 Days)</div>
                        <div style={{ color: '#16a34a', fontSize: 8.5, fontWeight: 700 }}>Confidence: 98%</div>
                      </div>
                      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: 6 }}>
                        <div style={{ color: '#64748b', fontSize: 9 }}>Next Service</div>
                        <div style={{ fontWeight: 900, color: '#0b3b60', fontSize: 11.5 }}>Oil & Filter</div>
                        <div style={{ color: '#ea580c', fontSize: 8.5, fontWeight: 700 }}>In 184 running hrs</div>
                      </div>
                      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: 6 }}>
                        <div style={{ color: '#64748b', fontSize: 9 }}>Piston Wear</div>
                        <div style={{ fontWeight: 900, color: '#0b3b60', fontSize: 11.5 }}>1.4% (Minimal)</div>
                        <div style={{ color: '#16a34a', fontSize: 8.5, fontWeight: 700 }}>No leaks</div>
                      </div>
                      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: 6 }}>
                        <div style={{ color: '#64748b', fontSize: 9 }}>Insulation</div>
                        <div style={{ fontWeight: 900, color: '#0b3b60', fontSize: 11.5 }}>Dry & Safe</div>
                        <div style={{ color: '#16a34a', fontSize: 8.5, fontWeight: 700 }}>Heater On</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Side: Power Summary & Controls */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: 12, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                    <div style={{ fontSize: 12, fontWeight: 900, color: '#0b3b60', marginBottom: 8 }}>
                      POWER SUMMARY
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: 4 }}>
                        <span style={{ color: '#64748b' }}>Generator:</span>
                        <strong style={{ color: '#0f172a' }}>{genOutput.toFixed(1)} kW</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: 4 }}>
                        <span style={{ color: '#64748b' }}>Solar / Wind:</span>
                        <strong style={{ color: '#16a34a' }}>{Math.round(((solarGen + windGen) / currentTotalLoad) * 100)}%</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: 4 }}>
                        <span style={{ color: '#64748b' }}>Battery:</span>
                        <strong style={{ color: '#8b5cf6' }}>{batterySoC}%</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: 4 }}>
                        <span style={{ color: '#64748b' }}>CO₂ Saved:</span>
                        <strong style={{ color: '#16a34a' }}>48.2 kg</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ═══════════ TAB 2: GENERATOR FLEET (DG 1-4) ═══════════ */}
            {activeTab === 'generators' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
                {[
                  { id: 1, name: 'Generator 1 (Main Power)', status: 'Running (Main)', kw: Math.round(genOutput * 0.65), rpm: 1500, coolant: 82, oilPress: 4.8, egt: 410, fuelLhr: 18.2 },
                  { id: 2, name: 'Generator 2 (Extra Power)', status: genOutput > 70 ? 'Running (Assisting)' : 'Ready (Standby)', kw: genOutput > 70 ? Math.round(genOutput * 0.35) : 0, rpm: genOutput > 70 ? 1500 : 0, coolant: 64, oilPress: genOutput > 70 ? 4.7 : 0, egt: genOutput > 70 ? 385 : 45, fuelLhr: genOutput > 70 ? 12.1 : 0 },
                  { id: 3, name: 'Generator 3 (Auto-Backup)', status: 'Ready (Standby)', kw: 0, rpm: 0, coolant: 58, oilPress: 0, egt: 28, fuelLhr: 0 },
                  { id: 4, name: 'Generator 4 (Emergency)', status: 'Emergency Reserve', kw: 0, rpm: 0, coolant: 42, oilPress: 0, egt: 22, fuelLhr: 0 },
                ].map((gen) => {
                  const isRunning = gen.status.includes('Running')
                  return (
                    <div
                      key={gen.id}
                      onClick={() => setSelectedGen(gen.id)}
                      style={{
                        background: '#ffffff',
                        border: selectedGen === gen.id ? '2px solid #0284c7' : '1px solid #cbd5e1',
                        borderTop: isRunning ? '4px solid #16a34a' : '4px solid #94a3b8',
                        padding: 14,
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, borderBottom: '1px solid #f1f5f9', paddingBottom: 6 }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 900, color: '#0b3b60' }}>{gen.name}</div>
                          <div style={{ fontSize: 9.5, color: '#64748b' }}>ID: GEN-0{gen.id} (100 kVA)</div>
                        </div>
                        <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 6px', background: isRunning ? '#dcfce7' : '#f1f5f9', color: isRunning ? '#15803d' : '#64748b', borderRadius: 2 }}>
                          {gen.status}
                        </span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11, marginBottom: 10 }}>
                        <div style={{ background: '#f8fafc', padding: 6, border: '1px solid #e2e8f0' }}>
                          <div style={{ color: '#64748b', fontSize: 10 }}>Electricity</div>
                          <div style={{ fontWeight: 900, color: isRunning ? '#0284c7' : '#94a3b8', fontSize: 14 }}>{gen.kw} kW</div>
                        </div>
                        <div style={{ background: '#f8fafc', padding: 6, border: '1px solid #e2e8f0' }}>
                          <div style={{ color: '#64748b', fontSize: 10 }}>Speed</div>
                          <div style={{ fontWeight: 800, color: '#0f172a' }}>{gen.rpm} RPM</div>
                        </div>
                        <div style={{ background: '#f8fafc', padding: 6, border: '1px solid #e2e8f0' }}>
                          <div style={{ color: '#64748b', fontSize: 10 }}>Engine Heat</div>
                          <div style={{ fontWeight: 800, color: gen.coolant > 85 ? '#dc2626' : '#0f172a' }}>{gen.coolant} °C</div>
                        </div>
                        <div style={{ background: '#f8fafc', padding: 6, border: '1px solid #e2e8f0' }}>
                          <div style={{ color: '#64748b', fontSize: 10 }}>Oil Pressure</div>
                          <div style={{ fontWeight: 800, color: '#0f172a' }}>{gen.oilPress} bar</div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: 6 }}>
                        <button
                          onClick={() => triggerGenAction(gen.id, isRunning ? 'Turn Off / Move to Standby' : 'Turn On & Connect')}
                          style={{
                            flex: 1,
                            background: isRunning ? '#fee2e2' : '#dcfce7',
                            color: isRunning ? '#991b1b' : '#166534',
                            border: `1px solid ${isRunning ? '#fca5a5' : '#86efac'}`,
                            padding: '5px 8px',
                            fontSize: 10.5,
                            fontWeight: 800,
                            cursor: 'pointer',
                          }}
                        >
                          {isRunning ? 'Turn Off' : 'Turn On'}
                        </button>
                        <button
                          onClick={() => triggerGenAction(gen.id, 'Self-Check Routine')}
                          style={{
                            background: '#ffffff',
                            color: '#0b3b60',
                            border: '1px solid #cbd5e1',
                            padding: '5px 8px',
                            fontSize: 10.5,
                            fontWeight: 700,
                            cursor: 'pointer',
                          }}
                        >
                          Test Engine
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* ═══════════ TAB 3: FUEL STORAGE TANKS ═══════════ */}
            {activeTab === 'fuel' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
                {[
                  { id: 'T1', name: 'Tank 1 — Daily Generator Tank', capacity: 5000, current: 4350, temp: 12, status: 'Ready to Use' },
                  { id: 'T2', name: 'Tank 2 — Main Storage (Tank A)', capacity: 75000, current: 63200, temp: 6, status: 'Normal' },
                  { id: 'T3', name: 'Tank 3 — Main Storage (Tank B)', capacity: 75000, current: 59100, temp: 5, status: 'Normal' },
                  { id: 'T4', name: 'Tank 4 — Emergency Reserve Tank', capacity: 10000, current: 9800, temp: 8, status: 'Emergency Only' },
                ].map((tank) => {
                  const pct = Math.round((tank.current / tank.capacity) * 100)
                  return (
                    <div key={tank.id} style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: 14, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <span style={{ fontSize: 12.5, fontWeight: 900, color: '#0b3b60' }}>{tank.name}</span>
                        <span style={{ fontSize: 9.5, fontWeight: 800, color: tank.status === 'Emergency Only' ? '#b45309' : '#0369a1', background: tank.status === 'Emergency Only' ? '#fef3c7' : '#e0f2fe', padding: '2px 7px', borderRadius: 2 }}>
                          {tank.status}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '8px 0' }}>
                        <span style={{ fontSize: 22, fontWeight: 900, color: '#0f172a' }}>{tank.current.toLocaleString()}</span>
                        <span style={{ fontSize: 11, color: '#64748b' }}>/ {tank.capacity.toLocaleString()} Litres ({pct}% full)</span>
                      </div>

                      {/* Progress Bar */}
                      <div style={{ height: 10, background: '#e2e8f0', borderRadius: 2, overflow: 'hidden', marginBottom: 8 }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: pct > 30 ? '#0284c7' : '#ea580c' }} />
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: '#475569' }}>
                        <span>Tank Heater: <strong>{tank.temp}°C (Anti-freeze)</strong></span>
                        <span>Fuel Quality: <strong>100% Pure</strong></span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* ═══════════ TAB 4: FUEL PREDICTOR ═══════════ */}
            {activeTab === 'prediction' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 14 }}>
                <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                  <h3 style={{ fontSize: 13, fontWeight: 900, color: '#0b3b60', marginTop: 0, marginBottom: 4 }}>
                    ⛽ FUEL PREDICTOR
                  </h3>
                  <div style={{ fontSize: 10.5, color: '#64748b', marginBottom: 14 }}>
                    Move the sliders to see how cold weather and crew size change diesel fuel usage.
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 16 }}>
                    {/* Control 1: Temperature */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>
                        <span>Outside Temperature</span>
                        <span style={{ color: '#0284c7', fontSize: 13 }}>{ambientTemp} °C</span>
                      </div>
                      <input
                        type="range"
                        min="-55"
                        max="-5"
                        value={ambientTemp}
                        onChange={(e) => setAmbientTemp(parseInt(e.target.value))}
                        style={{ width: '100%', cursor: 'pointer' }}
                      />
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: '#94a3b8' }}>
                        <span>-55°C (Extreme Cold)</span>
                        <span>-5°C (Mild Summer)</span>
                      </div>
                    </div>

                    {/* Control 2: Occupancy */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontWeight: 800, color: '#0b3b60', marginBottom: 4 }}>
                        <span>Station Crew Size</span>
                        <span style={{ color: '#0284c7', fontSize: 13 }}>{crewOccupancy} People</span>
                      </div>
                      <input
                        type="range"
                        min="10"
                        max="60"
                        value={crewOccupancy}
                        onChange={(e) => setCrewOccupancy(parseInt(e.target.value))}
                        style={{ width: '100%', cursor: 'pointer' }}
                      />
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: '#94a3b8' }}>
                        <span>10 People (Winter Team)</span>
                        <span>60 People (Summer Team)</span>
                      </div>
                    </div>
                  </div>

                  {/* Prediction Highlights */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, background: '#f8fafc', padding: 12, border: '1px solid #e2e8f0' }}>
                    <div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>Electricity Needed</div>
                      <div style={{ fontSize: 17, fontWeight: 900, color: '#0b3b60' }}>{currentTotalLoad} kW</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>Daily Diesel Used</div>
                      <div style={{ fontSize: 17, fontWeight: 900, color: '#ea580c' }}>{dailyBurnLitres} Litres</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>Days Fuel Will Last</div>
                      <div style={{ fontSize: 17, fontWeight: 900, color: '#16a34a' }}>{daysOfAutonomy} Days</div>
                    </div>
                  </div>
                </div>

                {/* Resupply Mission Tracker */}
                <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: 16, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                  <h4 style={{ fontSize: 12, fontWeight: 900, color: '#0b3b60', marginTop: 0, marginBottom: 8 }}>
                    🚢 NEXT RESUPPLY SHIP
                  </h4>
                  <div style={{ fontSize: 10.5, color: '#475569', lineHeight: 1.5, marginBottom: 12 }}>
                    Supply Ship: <strong>MV Vasiliy Golovnin</strong>
                  </div>

                  <div style={{ background: '#f0f9ff', padding: 10, border: '1px solid #bae6fd', marginBottom: 10 }}>
                    <div style={{ fontSize: 10, color: '#0369a1', fontWeight: 800 }}>Ship Arrival:</div>
                    <div style={{ fontSize: 15, fontWeight: 900, color: '#0b3b60', marginTop: 2 }}>In 68 Days</div>
                    <div style={{ fontSize: 9.5, color: '#0369a1', marginTop: 4 }}>
                      Safety Buffer: <strong>+{(daysOfAutonomy - 68)} extra days of fuel</strong>
                    </div>
                  </div>

                  <div style={{ fontSize: 10, color: '#16a34a', fontWeight: 700 }}>
                    ✓ Safe: Enough fuel until ship arrives
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
