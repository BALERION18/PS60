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

// ── Accordion Section Header ─────────────────────────────────────────────────
interface SectionHeaderProps {
  icon: string
  title: string
  badge?: string
  badgeColor?: string
  isOpen: boolean
  onToggle: () => void
  accentColor?: string
}

function SectionHeader({
  icon, title, badge, badgeColor = '#6F8747', isOpen, onToggle, accentColor = '#4F5935',
}: SectionHeaderProps) {
  return (
    <button
      onClick={onToggle}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 14px',
        background: isOpen ? '#F6F3ED' : '#FCFBF8',
        border: '1px solid #DDD8CC',
        borderLeft: `3px solid ${accentColor}`,
        cursor: 'pointer',
        fontFamily: 'Inter',
        borderRadius: isOpen ? '8px 8px 0 0' : 8,
        transition: 'all 0.15s',
        textAlign: 'left',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 16, color: accentColor }}
        >
          {icon}
        </span>
        <span style={{ fontSize: 11.5, fontWeight: 800, color: '#252820', letterSpacing: '0.03em' }}>
          {title}
        </span>
        {badge && (
          <span
            style={{
              fontSize: 8.5,
              fontWeight: 800,
              color: badgeColor,
              background: badgeColor + '18',
              border: `1px solid ${badgeColor}44`,
              padding: '1px 7px',
              borderRadius: 3,
              letterSpacing: '0.04em',
            }}
          >
            {badge}
          </span>
        )}
      </div>
      <span
        className="material-symbols-outlined"
        style={{
          fontSize: 18,
          color: '#8A9088',
          transition: 'transform 0.2s',
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
        }}
      >
        expand_more
      </span>
    </button>
  )
}

// ── Collapsible Section Wrapper ───────────────────────────────────────────────
interface SectionProps {
  icon: string
  title: string
  badge?: string
  badgeColor?: string
  accentColor?: string
  defaultOpen?: boolean
  sectionKey: string
  openSections: Record<string, boolean>
  setOpenSections: React.Dispatch<React.SetStateAction<Record<string, boolean>>>
  children: React.ReactNode
}

function Section({
  icon, title, badge, badgeColor, accentColor, sectionKey,
  openSections, setOpenSections, children,
}: SectionProps) {
  const isOpen = openSections[sectionKey] ?? true

  function toggle() {
    setOpenSections(prev => ({ ...prev, [sectionKey]: !isOpen }))
  }

  return (
    <div style={{ marginBottom: 10 }}>
      <SectionHeader
        icon={icon}
        title={title}
        badge={badge}
        badgeColor={badgeColor}
        accentColor={accentColor}
        isOpen={isOpen}
        onToggle={toggle}
      />
      {isOpen && (
        <div
          style={{
            border: '1px solid #DDD8CC',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            background: '#F6F3ED',
            padding: 10,
          }}
        >
          {children}
        </div>
      )}
    </div>
  )
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [activeStation, setActiveStation] = useState<string>('maitri')
  const [timeRange, setTimeRange] = useState<string>('1H')
  const { t } = useLanguage()

  // Per-station section open/close state — both stations independent
  const [maitriSections, setMaitriSections] = useState<Record<string, boolean>>({
    twin:        true,
    operational: true,
    telemetry:   false,
  })
  const [bharatiSections, setBharationSections] = useState<Record<string, boolean>>({
    twin:        true,
    operational: true,
    telemetry:   false,
  })

  const openSections   = activeStation === 'maitri' ? maitriSections   : bharatiSections
  const setOpenSections = activeStation === 'maitri' ? setMaitriSections : setBharationSections

  function toggleStation() {
    setActiveStation(s => s === 'maitri' ? 'bharati' : 'maitri')
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}>
      <TopNav />
      <AlertStrip />

      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar activeStation={activeStation} onSwitchStation={toggleStation} />

        <main
          id="main-content"
          style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#E9E3D7' }}
        >
          <div style={{ flex: 1, padding: '8px 12px 20px 12px' }}>

            {/* ── Breadcrumb Bar ── */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: 10.5,
                color: '#687066',
                marginBottom: 8,
                padding: '4px 10px',
                background: '#FCFBF8',
                border: '1px solid #DDD8CC',
                boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                borderRadius: 4,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#4F5935' }}>home</span>
                <span style={{ color: '#4F5935', fontWeight: 700 }}>{t('crumb.home')}</span>
                <span>&gt;</span>
                <span style={{ color: '#4F5935', fontWeight: 600 }}>{t('crumb.polar_division')}</span>
                <span>&gt;</span>
                <span style={{ color: '#4F5935', fontWeight: 800 }}>{t('crumb.twin')}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* Quick expand/collapse all */}
                <button
                  onClick={() => setOpenSections({ twin: true, operational: true, telemetry: true })}
                  style={{
                    fontSize: 9.5, fontWeight: 700, color: '#4F5935',
                    background: 'transparent', border: '1px solid #DDD8CC',
                    padding: '2px 8px', cursor: 'pointer', borderRadius: 3,
                    display: 'flex', alignItems: 'center', gap: 4,
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 12 }}>unfold_more</span>
                  Expand All
                </button>
                <button
                  onClick={() => setOpenSections({ twin: false, operational: false, telemetry: false })}
                  style={{
                    fontSize: 9.5, fontWeight: 700, color: '#687066',
                    background: 'transparent', border: '1px solid #DDD8CC',
                    padding: '2px 8px', cursor: 'pointer', borderRadius: 3,
                    display: 'flex', alignItems: 'center', gap: 4,
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 12 }}>unfold_less</span>
                  Collapse All
                </button>
                <span
                  style={{
                    fontSize: 9.5, color: '#6F8747', background: '#E4E8D3',
                    padding: '2px 8px', fontWeight: 800, border: '1px solid #C5D4A8', borderRadius: 2,
                  }}
                >
                  🟢 2/2 STATIONS LIVE
                </span>
              </div>
            </div>

            {/* ── Station Selector ── */}
            <StationTabs
              active={activeStation}
              onSelect={setActiveStation}
              timeRange={timeRange}
              onTimeRange={setTimeRange}
            />

            {/* ══════════════════════════════════════════════════════════
                SECTION 1 — Live Station Schematic
            ══════════════════════════════════════════════════════════ */}
            <Section
              sectionKey="twin"
              icon="satellite_alt"
              title={activeStation === 'maitri' ? 'MAITRI — Live Station View' : 'BHARATI — Live Station View'}
              badge="LIVE"
              badgeColor="#6F8747"
              accentColor="#4F5935"
              openSections={openSections}
              setOpenSections={setOpenSections}
            >
              <SchematicPanel stationId={activeStation} />
            </Section>

            {/* ══════════════════════════════════════════════════════════
                SECTION 2 — Operational Status (Weather + Energy + Alerts)
            ══════════════════════════════════════════════════════════ */}
            <Section
              sectionKey="operational"
              icon="monitor_heart"
              title="OPERATIONAL STATUS"
              badge="3 PANELS"
              badgeColor="#C58A32"
              accentColor="#C58A32"
              openSections={openSections}
              setOpenSections={setOpenSections}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: 10,
                }}
              >
                {/* Weather */}
                <div>
                  <div style={{ fontSize: 9, fontWeight: 800, color: '#687066', letterSpacing: '0.06em', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#6F8747' }}>thermostat</span>
                    WEATHER & CLIMATE
                  </div>
                  <WeatherCard stationId={activeStation} />
                </div>

                {/* Energy */}
                <div>
                  <div style={{ fontSize: 9, fontWeight: 800, color: '#687066', letterSpacing: '0.06em', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#C58A32' }}>bolt</span>
                    ENERGY & FUEL
                  </div>
                  <EnergyCard stationId={activeStation} />
                </div>

                {/* Alerts */}
                <div>
                  <div style={{ fontSize: 9, fontWeight: 800, color: '#687066', letterSpacing: '0.06em', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#B85A5A' }}>notifications_active</span>
                    ACTIVE ALERTS
                  </div>
                  <ActiveAlerts stationId={activeStation} />
                </div>
              </div>
            </Section>

            {/* ══════════════════════════════════════════════════════════
                SECTION 3 — Scientific Telemetry (collapsed by default)
            ══════════════════════════════════════════════════════════ */}
            <Section
              sectionKey="telemetry"
              icon="sensors"
              title="SCIENTIFIC TELEMETRY"
              badge="COLLAPSED"
              badgeColor="#8278A4"
              accentColor="#8278A4"
              openSections={openSections}
              setOpenSections={setOpenSections}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: 10,
                }}
              >
                {/* Met Mast */}
                <div>
                  <div style={{ fontSize: 9, fontWeight: 800, color: '#687066', letterSpacing: '0.06em', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#8278A4' }}>cell_tower</span>
                    MET MAST — WIND & PRESSURE
                  </div>
                  <MetMastCard stationId={activeStation} />
                </div>

                {/* Glacial / Life Support */}
                <div>
                  <div style={{ fontSize: 9, fontWeight: 800, color: '#687066', letterSpacing: '0.06em', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#76804D' }}>water_drop</span>
                    ICE RADAR & LIFE SUPPORT
                  </div>
                  <GlacialCard stationId={activeStation} />
                </div>

                {/* Satellite / Survival */}
                <div>
                  <div style={{ fontSize: 9, fontWeight: 800, color: '#687066', letterSpacing: '0.06em', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 12, color: '#4F5935' }}>satellite_alt</span>
                    SATELLITE LINK & AUTONOMY
                  </div>
                  <SeismicCard stationId={activeStation} />
                </div>
              </div>
            </Section>

          </div>
        </main>
      </div>

      <Footer />
    </div>
  )
}
