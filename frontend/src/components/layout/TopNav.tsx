import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useLanguage } from '../../context/LanguageContext'

export default function TopNav() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { lang, toggleLang, t } = useLanguage()
  const [timeStr, setTimeStr] = useState<string>('')

  useEffect(() => {
    function updateClock() {
      const now = new Date()
      const options: Intl.DateTimeFormatOptions = {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }
      setTimeStr(new Intl.DateTimeFormat(lang === 'hi' ? 'hi-IN' : 'en-IN', options).format(now) + ' IST')
    }
    updateClock()
    const timer = setInterval(updateClock, 1000)
    return () => clearInterval(timer)
  }, [lang])

  return (
    <header className="w-full shrink-0 z-50 flex flex-col bg-white shadow-sm">
      {/* ── Tier 1: National Tricolour Stripe ── */}
      <div className="tricolour-ribbon" />

      {/* ── Tier 1: Top Bar ── */}
      <div
        style={{
          background: '#FCFBF8',
          borderBottom: '1px solid #E9E5DC',
          padding: '3px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: '#687066',
        }}
      >
        {/* Left: Date & Time with clock icon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#4F5935', fontFamily: 'Inter', fontWeight: 700, fontSize: 10.5 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#ea580c' }}>calendar_month</span>
          <span>{timeStr || 'LIVE IST'}</span>
        </div>

        {/* Right: Language Switch */}
        <div>
          <button
            onClick={toggleLang}
            style={{
              background: '#4F5935',
              border: '1px solid #082842',
              color: '#ffffff',
              fontSize: 11,
              fontWeight: 800,
              padding: '4px 14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              borderRadius: 20,
              boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
              transition: 'background 0.15s',
            }}
            title={lang === 'hi' ? 'Switch portal to English' : 'पोर्टल को हिंदी में बदलें'}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#D4883A' }}>translate</span>
            <span>{lang === 'hi' ? 'English' : 'हिन्दी'}</span>
          </button>
        </div>
      </div>

      {/* ── Tier 2: The Iconic Official White Government Masthead ── */}
      <div
        style={{
          background: '#ffffff',
          padding: '5px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '2px solid #D4883A',
        }}
      >
        {/* Left: Ministry Hierarchy & Application Brand */}
        <div
          onClick={() => navigate('/')}
          style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
          title="HIMADRI Home"
        >
          {/* Official Circular NCPOR Logo */}
          <img
            src="/himadri_logo.png"
            alt="HIMADRI Logo"
            style={{ height: 62, width: 62, objectFit: 'contain', display: 'block', flexShrink: 0 }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {/* Tier A: Organisation Name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
              <span style={{ fontSize: 9, fontWeight: 700, background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe', padding: '1px 6px', borderRadius: 3 }}>
                MoES
              </span>
            </div>

            {/* Tier B: Main Application Brand Logo & Title */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, lineHeight: 1.2 }}>
              <span style={{ fontSize: 16, fontWeight: 900, color: '#1e3a5f', letterSpacing: '0.04em' }}>
                HIMADRI
              </span>
              <span style={{ fontSize: 13.5, fontWeight: 800, color: '#252820', letterSpacing: '-0.01em' }}>
                {t('app.title')}
              </span>
            </div>
            <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, marginTop: 2, fontStyle: 'italic' }}>
              Smarter Antarctic Station Management
            </div>
          </div>
        </div>

        {/* Right: Digital India Badge + Officer Info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>

          {/* Officer Profile & Logout */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              background: '#F6F3ED',
              border: '1px solid #DDD8CC',
              padding: '5px 12px',
            }}
          >
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: '#4F5935', lineHeight: 1.1 }}>
                {user?.username ? user.username.toUpperCase() : 'OFFICER'}
              </div>
            </div>

            <button
              onClick={logout}
              style={{
                background: '#dc2626',
                border: 'none',
                color: '#ffffff',
                padding: '5px 14px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                fontWeight: 800,
                borderRadius: 20,
                boxShadow: '0 1px 2px rgba(220, 38, 38, 0.2)',
              }}
              title={t('header.logout')}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 13 }}>logout</span>
              <span className="hidden sm:inline">{t('header.logout')}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}


