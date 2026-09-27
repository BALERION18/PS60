import { useState } from 'react'
import TopNav from '../components/layout/TopNav'
import AlertStrip from '../components/layout/AlertStrip'
import Sidebar from '../components/layout/Sidebar'
import Footer from '../components/layout/Footer'
import StationTabs from '../components/dashboard/StationTabs'
import SchematicPanel from '../components/dashboard/SchematicPanel'
import WeatherCard from '../components/dashboard/WeatherCard'
import EnergyCard from '../components/dashboard/EnergyCard'
import ActiveAlerts from '../components/dashboard/ActiveAlerts'
import MetMastCard from '../components/dashboard/MetMastCard'
import GlacialCard from '../components/dashboard/GlacialCard'
import SeismicCard from '../components/dashboard/SeismicCard'
import { useLanguage } from '../context/LanguageContext'

export default function DashboardPage() {
  const [activeStation, setActiveStation] = useState<string>('maitri')
  const [timeRange, setTimeRange] = useState<string>('1H')
  const { t } = useLanguage()

  function toggleStation() {
    setActiveStation(s => s === 'maitri' ? 'bharati' : 'maitri')
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
      <TopNav />
      <AlertStrip />

      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar activeStation={activeStation} onSwitchStation={toggleStation} />

        <main id="main-content" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
          <div style={{ flex: 1, padding: '8px 12px 20px 12px' }}>
            {/* Official Government Breadcrumbs Bar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: 10.5,
                color: '#64748b',
                marginBottom: 8,
                padding: '4px 10px',
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#0b3b60' }}>home</span>
                <span style={{ color: '#0b3b60', fontWeight: 700 }}>{t('crumb.home')}</span>
                <span>&gt;</span>
                <span style={{ color: '#0b3b60', fontWeight: 600 }}>{t('crumb.polar_division')}</span>
                <span>&gt;</span>
                <span style={{ color: '#0b3b60', fontWeight: 800 }}>{t('crumb.twin')}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 9.5, color: '#15803d', background: '#dcfce7', padding: '2px 8px', fontWeight: 800, border: '1px solid #bbf7d0', borderRadius: 2 }}>
                  🟢 2/2 STATIONS LIVE
                </span>
              </div>
            </div>

            <StationTabs
              active={activeStation}
              onSelect={setActiveStation}
              timeRange={timeRange}
              onTimeRange={setTimeRange}
            />

            {/* Bento Grid */}
            <div className="bento-grid">
              {/* ── Centre: Schematic (responsive cols) ── */}
              <div className="bento-schematic">
                <SchematicPanel stationId={activeStation} />
              </div>

              {/* ── Right: Stacked cards (responsive cols) ── */}
              <div className="bento-side-stack">
                <WeatherCard stationId={activeStation} />
                <EnergyCard stationId={activeStation} />
                <ActiveAlerts stationId={activeStation} />
              </div>

              {/* ── Bottom Row ── */}
              <div className="bento-bottom-card">
                <MetMastCard stationId={activeStation} />
              </div>
              <div className="bento-bottom-card">
                <GlacialCard stationId={activeStation} />
              </div>
              <div className="bento-bottom-card">
                <SeismicCard stationId={activeStation} />
              </div>
            </div>
          </div>
        </main>
      </div>

      <Footer />
    </div>
  )
}
