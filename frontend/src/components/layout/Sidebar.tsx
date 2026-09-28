import { useNavigate, useLocation } from 'react-router-dom'
import { useLanguage } from '../../context/LanguageContext'

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
        borderRight: '1px solid #DDD8CC',
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
      {/* Wing Banner — text only */}
      <div
        className="sidebar-emblem"
        style={{
          padding: '8px 10px',
          borderBottom: '1px solid #DDD8CC',
          background: '#F6F3ED',
        }}
      >
        <div>
          <div style={{ fontSize: 8.5, fontWeight: 700, letterSpacing: '0.06em', color: '#C58A32' }}>
            {t('nav.wing_title')}
          </div>
          <div style={{ fontSize: 12, fontWeight: 800, color: '#252820', lineHeight: 1.15 }}>
            {t('nav.wing_sub')}
          </div>
          <div style={{ fontSize: 8, fontWeight: 600, color: '#8A9088', letterSpacing: '0.03em', marginTop: 2 }}>
            HIMADRI • NCPOR
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
                background: active ? '#E4E8D3' : 'transparent',
                borderLeft: active ? '3px solid #76804D' : '3px solid transparent',
                borderBottom: '1px solid #E9E5DC',
              }}
              onMouseOver={(e) => {
                if (!active) (e.currentTarget as HTMLElement).style.background = '#F6F3ED'
              }}
              onMouseOut={(e) => {
                if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent'
              }}
            >
              <span
                className="material-symbols-outlined"
                style={{
                  fontSize: 18,
                  color: active ? '#76804D' : '#8A9088',
                  flexShrink: 0,
                }}
              >
                {item.icon}
              </span>
              <div className="sidebar-label" style={{ lineHeight: 1.2 }}>
                <div style={{ fontSize: 11.5, fontWeight: active ? 800 : 600, color: active ? '#4F5935' : '#252820' }}>
                  {item.label}
                </div>
                <div style={{ fontSize: 8.5, color: '#8A9088', fontWeight: 500 }}>
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

