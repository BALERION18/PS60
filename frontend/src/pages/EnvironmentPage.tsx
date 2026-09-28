import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import { useSensors } from '../hooks/useSensors'
import PageSection from '../components/ui/PageSection'

type StationId = 'maitri' | 'bharati'
type TabType = 'overview' | 'atmosphere' | 'glaciology' | 'seismic' | 'ocean'

const STATIONS: Record<StationId, { name: string; coords: string; elevation: string; region: string }> = {
  maitri: { name: 'Maitri Research Station', coords: '70°45′S, 11°44′E', elevation: '130m ASL', region: 'Schirmacher Oasis, Queen Maud Land' },
  bharati: { name: 'Bharati Research Station', coords: '69°24′S, 76°11′E', elevation: '35m ASL', region: 'Larsemann Hills, Prydz Bay' },
}

type SensorRow = { sensor_id: string; latest_value: number | null }
function sv(sensors: SensorRow[] | undefined, keyword: string): number | null {
  if (!sensors) return null
  return sensors.find(x => x.sensor_id.toLowerCase().includes(keyword))?.latest_value ?? null
}
function fmt(v: number | null, decimals = 1): string {
  return v === null ? '—' : v.toFixed(decimals)
}

function MetCard({ label, value, unit, icon, color, sub }: { label: string; value: string | number; unit: string; icon: string; color: string; sub?: string }) {
  return (
    <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '14px', display: 'flex', flexDirection: 'column', gap: 4, boxShadow: '0 1px 3px rgba(0,0,0,0.04)', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, width: 3, height: '100%', background: color }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginLeft: 8 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', letterSpacing: '0.05em', textTransform: 'uppercase' }}>{label}</div>
        <span className="material-symbols-outlined" style={{ fontSize: 16, color }}>{icon}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginLeft: 8 }}>
        <span style={{ fontSize: 24, fontWeight: 800, color: '#252820', fontFamily: 'Inter' }}>{value}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#687066' }}>{unit}</span>
      </div>
      {sub && <div style={{ fontSize: 10, color: '#8A9088', marginLeft: 8 }}>{sub}</div>}
    </div>
  )
}

export default function EnvironmentPage() {
  const navigate = useNavigate()
  const [activeStation, setActiveStation] = useState<StationId>('maitri')
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [secTabs, setSecTabs] = useState(true)
  const st = STATIONS[activeStation]

  // ── Live sensor data from Neon ──────────────────────────────────────────
  const { data: weatherSensors } = useSensors(activeStation, 'weather')
  const { data: seismicSensors } = useSensors(activeStation, 'seismic')

  const env = {
    temp:       sv(weatherSensors, 'temperature'),
    wind:       sv(weatherSensors, 'wind_speed'),
    wind_dir:   sv(weatherSensors, 'wind_dir'),
    humidity:   sv(weatherSensors, 'humidity'),
    pressure:   sv(weatherSensors, 'pressure'),
    snowfall:   sv(weatherSensors, 'snowfall'),
    radiation:  sv(weatherSensors, 'radiation'),
    seismicPgv: sv(seismicSensors, 'pgv'),
    magnitude:  sv(seismicSensors, 'magnitude'),
  }


  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'overview', label: 'Met Overview', icon: 'cloud' },
    { id: 'atmosphere', label: 'Atmosphere', icon: 'air' },
    { id: 'glaciology', label: 'Glaciology', icon: 'ac_unit' },
    { id: 'seismic', label: 'Seismic & Geophysics', icon: 'vibration' },
    { id: 'ocean', label: 'Ocean & Ice', icon: 'waves' },
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
                <span>›</span><span style={{ color: '#C58A32', fontWeight: 800 }}>Environment & Met</span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <span style={{ fontSize: 10, color: '#6F8747', fontWeight: 700, background: '#E4E8D3', padding: '2px 8px', border: '1px solid #C5D4A8' }}>● SENSORS LIVE</span>
              </div>
            </div>
            <div style={{ background: '#4F5935', color: '#FCFBF8', padding: '10px 16px', marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 8 }}><span className="material-symbols-outlined" style={{ fontSize: 18 }}>air</span> {st.name.toUpperCase()} — ENVIRONMENTAL MONITORING</div>
                <div style={{ fontSize: 10, color: '#8A9088', marginTop: 2 }}>{st.coords} • {st.region} • {st.elevation}</div>
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
            <PageSection icon="sensors" title={`Environmental Data — ${activeTab.toUpperCase()}`} badge="LIVE SENSORS" badgeColor="#6F8747" accentColor="#4F5935" open={secTabs} onToggle={() => setSecTabs(v => !v)} bodyBg="#FCFBF8" bodyPadding={12}>
            {activeTab === 'overview' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {(env.temp !== null && env.temp < -30) && (<div style={{ background: '#FDF3E3', border: '1px solid #D4883A', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: 8 }}><span className="material-symbols-outlined" style={{ color: '#C58A32', fontSize: 18 }}>warning</span><span style={{ fontSize: 11, fontWeight: 700, color: '#92400e' }}>SEVERE WEATHER ALERT: Extreme cold advisory active — Temperature below -30°C. All external operations suspended.</span></div>)}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <MetCard label="AIR TEMPERATURE" value={fmt(env.temp)} unit="°C" icon="thermometer" color="#76804D" sub="Surface level" />
                  <MetCard label="WIND SPEED" value={fmt(env.wind)} unit="km/h" icon="air" color="#4F5935" sub={env.wind_dir !== null ? `Dir: ${Math.round(env.wind_dir ?? 0)}°` : 'Live from AWS'} />
                  <MetCard label="HUMIDITY" value={fmt(env.humidity, 0)} unit="%" icon="water_drop" color="#6F8747" sub="Relative humidity" />
                  <MetCard label="PRESSURE" value={fmt(env.pressure, 1)} unit="hPa" icon="compress" color="#C58A32" sub="Sea Level Ref." />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <MetCard label="SNOWFALL" value={fmt(env.snowfall, 1)} unit="mm" icon="ac_unit" color="#6F8747" sub="Fresh accumulation" />
                  <MetCard label="SEISMIC PGV" value={fmt(env.seismicPgv, 3)} unit="mm/s" icon="vibration" color="#8278A4" sub="Peak ground velocity" />
                  <MetCard label="SOLAR RADIATION" value={fmt(env.radiation, 2)} unit="kW/m²" icon="wb_sunny" color="#D4883A" sub="Global horizontal" />
                  <MetCard label="MAGNITUDE" value={fmt(env.magnitude, 2)} unit="Mw" icon="crisis_alert" color="#B85A5A" sub="Seismic magnitude" />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 12, letterSpacing: '0.05em' }}>IMD AUTO WEATHER STATION NETWORK</div>
                    {[{ name: 'Main AWS Station', status: 'ONLINE', last: '2 min ago', sensors: 18 },{ name: 'Summit Ridge AWS', status: 'ONLINE', last: '5 min ago', sensors: 12 },{ name: 'Ice Shelf Sensor Array', status: 'DEGRADED', last: '18 min ago', sensors: 6 },{ name: 'Upper Air Radiosonde', status: 'OFFLINE', last: '4h ago', sensors: 0 }].map(s => (
                      <div key={s.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid #F6F3ED', fontSize: 11 }}>
                        <div><div style={{ fontWeight: 700, color: '#252820' }}>{s.name}</div><div style={{ fontSize: 9, color: '#8A9088' }}>{s.sensors} sensors • {s.last}</div></div>
                        <span style={{ fontWeight: 800, fontSize: 10, color: s.status === 'ONLINE' ? '#6F8747' : s.status === 'DEGRADED' ? '#C58A32' : '#B85A5A', background: s.status === 'ONLINE' ? '#E4E8D3' : s.status === 'DEGRADED' ? '#FDF3E3' : '#F5E8E8', padding: '2px 8px', border: `1px solid ${s.status === 'ONLINE' ? '#C5D4A8' : s.status === 'DEGRADED' ? '#D5C490' : '#D4A5A5'}` }}>{s.status}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 12, letterSpacing: '0.05em' }}>IMD / ECMWF 5-DAY FORECAST</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
                      {['Today', 'D+1', 'D+2', 'D+3', 'D+4'].map((day, i) => {
                        const baseT = env.temp ?? -25
                        const baseW = env.wind ?? 50
                        const temps = [0, -3, 1, -5, 2].map(d => baseT + d)
                        const winds = [0, 10, -8, 20, -5].map(d => baseW + d)
                        const icons = ['storm', 'ac_unit', 'cloud', 'thunderstorm', 'partly_cloudy_day']
                        const labels = ['Blizzard', 'Snow', 'Overcast', 'Storm', 'Clearing']
                        return (<div key={day} style={{ background: i === 0 ? '#E4E8D3' : '#F6F3ED', border: `1px solid ${i === 0 ? '#D5D9C8' : '#E9E5DC'}`, padding: '10px 6px', textAlign: 'center' }}>
                          <div style={{ fontSize: 9, fontWeight: 800, color: '#4F5935' }}>{day}</div>
                          <span className="material-symbols-outlined" style={{ fontSize: 20, color: '#76804D', margin: '6px 0', display: 'block' }}>{icons[i]}</span>
                          <div style={{ fontSize: 12, fontWeight: 800, color: '#252820' }}>{temps[i].toFixed(1)}°</div>
                          <div style={{ fontSize: 8, color: '#687066' }}>{labels[i]}</div>
                          <div style={{ fontSize: 8, color: '#687066' }}>Wind: {Math.round(winds[i])} km/h</div>
                        </div>)
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}
            {activeTab === 'atmosphere' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <MetCard label="OZONE COLUMN" value="287" unit="DU" icon="layers" color="#8278A4" sub="Dobson Units — NOAA" />
                  <MetCard label="CO₂ LEVEL" value="412" unit="ppm" icon="co2" color="#6F8747" sub="Mauna Loa ref: 421" />
                  <MetCard label="SOLAR RADIATION" value={fmt(env.radiation, 2)} unit="kW/m²" icon="wb_sunny" color="#D4883A" sub="Global horizontal" />
                  <MetCard label="K-INDEX" value="2" unit="(Quiet)" icon="radio" color="#76804D" sub="Geomagnetic activity" />
                </div>
                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 12, letterSpacing: '0.05em' }}>UPPER AIR PROFILE — RADIOSONDE DATA (LAST ASCENT)</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, fontSize: 11 }}>
                    <div style={{ fontWeight: 700, color: '#687066', fontSize: 10, padding: '4px 0', borderBottom: '2px solid #4F5935' }}>ALTITUDE</div>
                    <div style={{ fontWeight: 700, color: '#687066', fontSize: 10, padding: '4px 0', borderBottom: '2px solid #4F5935' }}>TEMP</div>
                    <div style={{ fontWeight: 700, color: '#687066', fontSize: 10, padding: '4px 0', borderBottom: '2px solid #4F5935' }}>WIND</div>
                    <div style={{ fontWeight: 700, color: '#687066', fontSize: 10, padding: '4px 0', borderBottom: '2px solid #4F5935' }}>PRESSURE</div>
                    <div style={{ fontWeight: 700, color: '#687066', fontSize: 10, padding: '4px 0', borderBottom: '2px solid #4F5935' }}>HUMIDITY</div>
                    {[{ alt: '10 km', temp: -56.2, wind: '142 WNW', p: '264 hPa', rh: '18%' },{ alt: '5 km', temp: -38.7, wind: '98 SW', p: '540 hPa', rh: '32%' },{ alt: '2 km', temp: -33.1, wind: '71 SW', p: '790 hPa', rh: '58%' },{ alt: '500 m', temp: -30.4, wind: '54 SSW', p: '920 hPa', rh: '71%' },{ alt: 'Surface', temp: env.temp ?? '—', wind: `${fmt(env.wind)} SW`, p: `${env.pressure !== null ? Math.round(env.pressure) : '—'} hPa`, rh: `${fmt(env.humidity, 0)}%` }].map(l => (
                      [<div key={l.alt+'a'} style={{ padding: '6px 0', borderBottom: '1px solid #F6F3ED', fontWeight: 800, color: '#4F5935', fontSize: 10 }}>{l.alt}</div>,
                      <div key={l.alt+'t'} style={{ padding: '6px 0', borderBottom: '1px solid #F6F3ED', color: '#76804D', fontWeight: 700 }}>{l.temp}°C</div>,
                      <div key={l.alt+'w'} style={{ padding: '6px 0', borderBottom: '1px solid #F6F3ED', color: '#4F5935', fontWeight: 700 }}>{l.wind}</div>,
                      <div key={l.alt+'p'} style={{ padding: '6px 0', borderBottom: '1px solid #F6F3ED', color: '#687066' }}>{l.p}</div>,
                      <div key={l.alt+'r'} style={{ padding: '6px 0', borderBottom: '1px solid #F6F3ED', color: '#6F8747', fontWeight: 700 }}>{l.rh}</div>]
                    ))}
                  </div>
                </div>
              </div>
            )}
            {activeTab === 'glaciology' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <MetCard label="SNOWFALL" value={fmt(env.snowfall, 1)} unit="mm" icon="ac_unit" color="#6F8747" sub="Fresh accumulation" />
                  <MetCard label="ICE THICKNESS" value="1.85" unit="m" icon="layers" color="#76804D" sub="Ground Penetrating Radar" />
                  <MetCard label="ALBEDO" value="0.87" unit="" icon="light_mode" color="#D4883A" sub="Snow-covered surface" />
                  <MetCard label="GLACIER FLOW" value="1.2" unit="m/yr" icon="trending_down" color="#8b5cf6" sub="Schirmacher retreat rate" />
                </div>
                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 14, letterSpacing: '0.05em' }}>CRYOSPHERE MONITORING — NCPOR GLACIOLOGY UNIT</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    {[{ label: 'Active Ice Core Sites', value: '3 Sites', sub: 'Depths: 12m, 24m, 150m', icon: 'circle', color: '#6F8747' },{ label: 'Permafrost Active Layer', value: '0.42 m', sub: 'Seasonal thaw depth', icon: 'terrain', color: '#C58A32' },{ label: 'Ice Sheet Velocity', value: '1.8 m/yr', sub: 'GPS-derived flow rate', icon: 'speed', color: '#76804D' },{ label: 'Surface Mass Balance', value: '-0.12 m/yr', sub: 'Sublimation loss', icon: 'scale', color: '#B85A5A' },{ label: 'Last ICESat-2 Pass', value: '2 days ago', sub: 'NASA polar orbit', icon: 'satellite', color: '#8278A4' },{ label: 'Ice Core Analysis', value: 'Active', sub: '150m deep, 800yr record', icon: 'science', color: '#6F8747' }].map(item => (
                      <div key={item.label} style={{ border: '1px solid #E9E5DC', padding: '12px', background: '#F6F3ED', display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 22, color: item.color, flexShrink: 0 }}>{item.icon}</span>
                        <div><div style={{ fontSize: 14, fontWeight: 800, color: '#252820' }}>{item.value}</div><div style={{ fontSize: 10, fontWeight: 700, color: '#4F5935' }}>{item.label}</div><div style={{ fontSize: 9, color: '#8A9088' }}>{item.sub}</div></div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            {activeTab === 'seismic' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <MetCard label="EARTHQUAKE LEVEL" value="Quiet" unit="" icon="vibration" color="#6F8747" sub="No tremors detected in 72h" />
                  <MetCard label="GROUND VIBRATION" value={env.seismicPgv !== null ? env.seismicPgv.toFixed(3) : '—'} unit="mm/s" icon="waves" color="#76804D" sub="Normal background vibration" />
                  <MetCard label="LOCAL GRAVITY" value="-18.4" unit="mGal" icon="height" color="#8278A4" sub="Natural polar gravity level" />
                  <MetCard label="COMPASS OFFSET" value="27.3°" unit="East" icon="explore" color="#C58A32" sub="Difference from true North" />
                </div>
                {/* Underground Ice & Ground Temperature Profile — Official Government Theme */}
                <div style={{ background: '#FCFBF8', border: '1px solid #DDD8CC', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
                  {/* Government Header Bar */}
                  <div
                    style={{
                      background: '#4F5935',
                      borderBottom: '2px solid #D4883A',
                      padding: '10px 14px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: 8,
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 800, color: '#FCFBF8', letterSpacing: '0.03em', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#D4883A' }}>thermostat</span>
                        UNDERGROUND ICE & GROUND TEMPERATURE — {activeStation === 'maitri' ? 'MAITRI BASE (SCHIRMACHER OASIS)' : 'BHARATI BASE (LARSEMANN HILLS)'}
                      </div>
                      <div style={{ fontSize: 10, color: '#DDD8CC', marginTop: 2, marginLeft: 22 }}>
                        National Centre for Polar and Ocean Research (MoES) • Multi-Depth Cryosphere Monitoring
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 10, color: '#FCFBF8', fontWeight: 800, background: '#072740', padding: '3px 8px', border: '1px solid #0d4775' }}>
                        CONSTANT TEMP: BELOW {activeStation === 'maitri' ? '11.4 m' : '9.8 m'}
                      </span>
                      <span style={{ fontSize: 10, color: '#4A6030', fontWeight: 800, background: '#E4E8D3', padding: '3px 8px', border: '1px solid #C5D4A8' }}>
                        ● GROUND FULLY FROZEN (STABLE)
                      </span>
                    </div>
                  </div>

                  <div style={{ padding: '14px' }}>
                    {/* Multi-depth Borehole Grid — Government Light Theme */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 10 }}>
                      {[
                        { depth: 'Surface (0 m)', temp: activeStation === 'maitri' ? '-28.4' : '-21.7', layer: 'Ground Surface', drift: '-0.02°C / yr', topColor: '#D4883A' },
                        { depth: '1.5 m Deep', temp: activeStation === 'maitri' ? '-19.8' : '-16.4', layer: 'Top Soil Layer', drift: '+0.01°C / yr', topColor: '#76804D' },
                        { depth: '5 m Deep', temp: activeStation === 'maitri' ? '-14.2' : '-12.1', layer: 'Frozen Ice & Soil', drift: '+0.01°C / yr', topColor: '#4F5935' },
                        { depth: '10 m Deep', temp: activeStation === 'maitri' ? '-11.6' : '-10.2', layer: 'Same Temp Year-Round', drift: '0.00°C (Stable)', topColor: '#4F5935' },
                        { depth: '25 m Deep', temp: activeStation === 'maitri' ? '-9.8' : '-8.9', layer: 'Deep Bedrock Under Ice', drift: '0.00°C (Stable)', topColor: '#1e3a8a' },
                        { depth: '50 m Deep', temp: activeStation === 'maitri' ? '-9.1' : '-8.4', layer: 'Deep Earth (50m)', drift: '0.00°C (Stable)', topColor: '#138808' },
                      ].map((b) => (
                        <div
                          key={b.depth}
                          style={{
                            background: '#F6F3ED',
                            border: '1px solid #DDD8CC',
                            borderTop: `3px solid ${b.topColor}`,
                            boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            padding: '10px 10px 8px',
                          }}
                        >
                          <div>
                            <div style={{ fontSize: 10, color: '#4F5935', fontWeight: 800, letterSpacing: '0.02em', borderBottom: '1px solid #E9E5DC', paddingBottom: 4 }}>
                              {b.depth}
                            </div>
                            <div style={{ fontSize: 22, fontWeight: 900, color: '#4F5935', fontFamily: 'Inter, sans-serif', margin: '8px 0 2px' }}>
                              {b.temp}°C
                            </div>
                            <div style={{ fontSize: 9.5, color: '#687066', fontWeight: 700, lineHeight: 1.2 }}>
                              {b.layer}
                            </div>
                          </div>
                          <div style={{ marginTop: 8, paddingTop: 6, borderTop: '1px dashed #E9E5DC' }}>
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 3,
                                fontSize: 9,
                                fontWeight: 700,
                                color: '#4A6030',
                                background: '#E4E8D3',
                                border: '1px solid #C5D4A8',
                                padding: '1px 5px',
                                borderRadius: 2,
                              }}
                            >
                              <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#6F8747' }} />
                              {b.drift}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Government Information Strip */}
                    <div
                      style={{
                        marginTop: 12,
                        background: '#F6F3ED',
                        border: '1px solid #DDD8CC',
                        borderLeft: '3px solid #4F5935',
                        padding: '8px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: 10.5,
                        flexWrap: 'wrap',
                        gap: 8,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div>
                          <span style={{ fontWeight: 700, color: '#687066' }}>Summer Thaw Depth: </span>
                          <strong style={{ color: '#4F5935' }}>{activeStation === 'maitri' ? '0.42 m (Top 42 cm melts in summer)' : '0.28 m (Top 28 cm melts in summer)'}</strong>
                        </div>
                        <span style={{ color: '#DDD8CC' }}>|</span>
                        <div>
                          <span style={{ fontWeight: 700, color: '#687066' }}>Solid Rock Starts At: </span>
                          <strong style={{ color: '#4F5935' }}>{activeStation === 'maitri' ? '28.5 m deep' : '41.2 m deep'}</strong>
                        </div>
                      </div>
                      <div style={{ color: '#687066', fontSize: 10 }}>
                        Telemetry Interval: <strong style={{ color: '#4F5935' }}>10 mins</strong> • Sensors: <strong style={{ color: '#4A6030' }}>All 6 Active (Pt100 RTD)</strong> • MoES Verified
                      </div>
                    </div>
                  </div>
                </div>
                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 12, letterSpacing: '0.05em' }}>RECENT EARTHQUAKES & ICE TREMORS — SURROUNDING REGION</div>
                  {[{ time: '48h ago', mag: 2.1, depth: '12 km deep', loc: '640 km NW — Bouvet Island', type: 'Distant Quake' },{ time: '5 days ago', mag: 4.7, depth: '8 km deep', loc: '1,240 km W — Scotia Ridge', type: 'Distant Quake' },{ time: '12 days ago', mag: 1.4, depth: '3 km deep', loc: '18 km East — Near station', type: 'Ice Crack' }].map(ev => (
                    <div key={ev.time} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #F6F3ED', fontSize: 11 }}>
                      <span style={{ fontWeight: 800, color: ev.mag > 4 ? '#B85A5A' : ev.mag > 2 ? '#C58A32' : '#6F8747', width: 40 }}>M{ev.mag}</span>
                      <span style={{ flex: 1, color: '#687066' }}>{ev.loc}</span>
                      <span style={{ color: '#8A9088', width: 90 }}>{ev.depth}</span>
                      <span style={{ fontSize: 10, color: '#4F5935', fontWeight: 700, background: '#E4E8D3', padding: '2px 6px', border: '1px solid #D5D9C8' }}>{ev.type}</span>
                      <span style={{ color: '#8A9088', width: 80, textAlign: 'right' }}>{ev.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {activeTab === 'ocean' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  <MetCard label="SEA ICE EXTENT" value="92.4" unit="%" icon="waves" color="#6F8747" sub="Above 30yr average" />
                  <MetCard label="OCEAN TEMP (SST)" value="-1.8" unit="°C" icon="thermostat" color="#76804D" sub="Southern Ocean Surface" />
                  <MetCard label="OCEAN SALINITY" value="34.7" unit="PSU" icon="water_drop" color="#8278A4" sub="Practical Salinity Units" />
                  <MetCard label="WAVE HEIGHT" value="4.2" unit="m" icon="tsunami" color="#C58A32" sub="Significant wave height" />
                </div>
                <div style={{ background: '#FCFBF8', border: '1px solid #E9E5DC', padding: '16px' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#687066', marginBottom: 14, letterSpacing: '0.05em' }}>ARGO FLOAT & MOORING ARRAY — SOUTHERN OCEAN NETWORK</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    {[{ name: 'Argo Float WMO-5906235', lat: '70.1°S', lon: '12.3°E', depth: '1,200m', temp: -1.4, sal: 34.6, status: 'ACTIVE' },{ name: 'Argo Float WMO-5906412', lat: '69.8°S', lon: '76.5°E', depth: '2,000m', temp: -1.8, sal: 34.7, status: 'ACTIVE' },{ name: 'NCPOR Mooring M-03', lat: '70.2°S', lon: '11.9°E', depth: '3,400m', temp: -0.8, sal: 34.9, status: 'ONLINE' }].map(f => (
                      <div key={f.name} style={{ border: '1px solid #E9E5DC', padding: '14px', background: '#F6F3ED' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                          <span style={{ fontSize: 10, fontWeight: 800, color: '#4F5935' }}>{f.name}</span>
                          <span style={{ fontSize: 9, color: '#6F8747', fontWeight: 800 }}>● {f.status}</span>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 10 }}>
                          <div><span style={{ color: '#8A9088' }}>Lat: </span><span style={{ fontWeight: 700 }}>{f.lat}</span></div>
                          <div><span style={{ color: '#8A9088' }}>Lon: </span><span style={{ fontWeight: 700 }}>{f.lon}</span></div>
                          <div><span style={{ color: '#8A9088' }}>Depth: </span><span style={{ fontWeight: 700 }}>{f.depth}</span></div>
                          <div><span style={{ color: '#8A9088' }}>Temp: </span><span style={{ fontWeight: 700, color: '#76804D' }}>{f.temp}°C</span></div>
                          <div><span style={{ color: '#8A9088' }}>Salinity: </span><span style={{ fontWeight: 700 }}>{f.sal} PSU</span></div>
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
