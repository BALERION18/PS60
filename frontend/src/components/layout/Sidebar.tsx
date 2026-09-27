import { useNavigate, useLocation } from 'react-router-dom'
import { useLanguage } from '../../context/LanguageContext'
import emblemOfIndia from '../../assets/emblem_of_india.svg'

export default function Sidebar({
  activeStation: _activeStation,
  onSwitchStation: _onSwitchStation,
}: {
  activeStation?: string
  onSwitchStation?: () => void
} = {}) {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useLanguage()

  const navItems = [
    { icon: 'dashboard', label: t('nav.dashboard'), sub: t('nav.dashboard_sub'), path: '/' },
    { icon: 'hub', label: t('nav.stations'), sub: t('nav.stations_sub'), path: '/stations' },
    { icon: 'bolt', label: t('nav.energy'), sub: t('nav.energy_sub'), path: '/energy' },
    { icon: 'local_shipping', label: t('nav.logistics'), sub: t('nav.logistics_sub'), path: '/logistics' },
    { icon: 'eco', label: t('nav.environment'), sub: t('nav.environment_sub'), path: '/environment' },
    { icon: 'foundation', label: t('nav.infrastructure'), sub: t('nav.infrastructure_sub'), path: '/infrastructure' },
    { icon: 'analytics', label: t('nav.analytics'), sub: t('nav.analytics_sub'), path: '/analytics' },
    { icon: 'description', label: t('nav.reports'), sub: t('nav.reports_sub'), path: '/reports' },
    { icon: 'settings', label: t('nav.settings'), sub: t('nav.settings_sub'), path: '/settings' },
  ]

  return (
    <aside
      style={{
        background: '#ffffff',
        borderRight: '1px solid #cbd5e1',
        width: 195,
        minWidth: 195,
        display: 'flex',
        flexDirection: 'column',
        position: 'sticky',
        top: 0,
        alignSelf: 'flex-start',
        height: '100vh',
        overflowY: 'auto',
        flexShrink: 0,
      }}
    >
      {/* Official Wing Emblem Banner */}
      <div
        className="sidebar-emblem"
        style={{
          padding: '8px 10px',
          borderBottom: '1px solid #cbd5e1',
          background: '#0b3b60',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 28,
              height: 32,
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              padding: '2px',
              borderRadius: 2,
            }}
          >
            <img
              src={emblemOfIndia}
              alt="Emblem Logo of India"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>
          <div>
            <div style={{ fontSize: 8.5, fontWeight: 700, letterSpacing: '0.06em', color: '#ff9933' }}>
              {t('nav.wing_title')}
            </div>
            <div style={{ fontSize: 12, fontWeight: 800, color: '#ffffff', lineHeight: 1.15 }}>
              {t('nav.wing_sub')}
            </div>
            <div style={{ fontSize: 8, fontWeight: 600, color: '#cbd5e1', letterSpacing: '0.03em' }}>
              V3.02 • NIC GOI
            </div>
          </div>
        </div>
      </div>

      {/* Nav items */}
      <nav
        style={{
          flex: 1,
          padding: '6px 8px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {navItems.map((item) => {
          const active = location.pathname === item.path
          return (
            <a
              key={item.path}
              href="#"
              onClick={(e) => {
                e.preventDefault()
                navigate(item.path)
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '7px 10px',
                textDecoration: 'none',
                transition: 'all 0.15s',
                background: active ? '#f0f9ff' : 'transparent',
                borderLeft: active ? '3px solid #0b3b60' : '3px solid transparent',
                borderBottom: '1px solid #f1f5f9',
              }}
              onMouseOver={(e) => {
                if (!active) (e.currentTarget as HTMLElement).style.background = '#f8fafc'
              }}
              onMouseOut={(e) => {
                if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent'
              }}
            >
              <span
                className="material-symbols-outlined"
                style={{
                  fontSize: 18,
                  color: active ? '#0b3b60' : '#64748b',
                  flexShrink: 0,
                }}
              >
                {item.icon}
              </span>
              <div className="sidebar-label" style={{ lineHeight: 1.2 }}>
                <div style={{ fontSize: 11.5, fontWeight: active ? 800 : 600, color: active ? '#0b3b60' : '#1e293b' }}>
                  {item.label}
                </div>
                <div style={{ fontSize: 8.5, color: '#64748b', fontWeight: 500 }}>
                  {item.sub}
                </div>
              </div>
            </a>
          )
        })}
      </nav>
    </aside>
  )
}

