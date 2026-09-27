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

      {/* ── Tier 1: Accessibility & Government of India National Bar (GIGW 3.0 Standard) ── */}
      <div
        style={{
          background: '#f8fafc',
          borderBottom: '1px solid #e2e8f0',
          padding: '3px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: '#334155',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Mini Indian Flag Emblem */}
          <div
            style={{
              width: 18,
              height: 12,
              display: 'flex',
              flexDirection: 'column',
              border: '1px solid #cbd5e1',
              overflow: 'hidden',
              flexShrink: 0,
            }}
          >
            <div style={{ flex: 1, background: '#FF9933' }} />
            <div style={{ flex: 1, background: '#FFFFFF', position: 'relative' }}>
              <div style={{ width: 3, height: 3, borderRadius: '50%', background: '#0B3B60', margin: 'auto' }} />
            </div>
            <div style={{ flex: 1, background: '#138808' }} />
          </div>

          <span style={{ fontWeight: 800, color: '#0f172a', letterSpacing: '0.02em' }}>
            {t('gov.title')}
          </span>
          <span style={{ color: '#94a3b8' }}>|</span>
          <span style={{ color: '#1e293b', fontWeight: 600 }}>
            {t('gov.ministry')}
          </span>
          <span style={{ color: '#94a3b8' }} className="hidden md:inline">•</span>
          <span style={{ color: '#475569' }} className="hidden md:inline">
            {t('gov.ncpor_short')}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {/* Dynamic Indian Standard Time */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#0b3b60', fontFamily: 'Inter', fontWeight: 700, fontSize: 10.5 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#ea580c' }}>schedule</span>
            <span>{timeStr || 'LIVE IST'}</span>
          </div>

          {/* Language Switch Button */}
          <button
            onClick={toggleLang}
            style={{
              background: '#0b3b60',
              border: '1px solid #082842',
              color: '#ffffff',
              fontSize: 11,
              fontWeight: 800,
              padding: '2px 10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
              transition: 'background 0.15s',
            }}
            title={lang === 'hi' ? 'Switch portal to English' : 'पोर्टल को हिंदी में बदलें'}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#ff9933' }}>translate</span>
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
          borderBottom: '2px solid #FF9933',
        }}
      >
        {/* Left: Ministry Hierarchy & Application Brand */}
        <div
          onClick={() => navigate('/')}
          style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
          title="HIMANTAR Home"
        >
          {/* Official Circular NCPOR Logo */}
          <img
            src="/ncpor_logo.png"
            alt="NCPOR Logo"
            style={{ height: 46, width: 46, objectFit: 'contain', display: 'block', flexShrink: 0 }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {/* Tier A: Organisation Name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#0369a1', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                {t('gov.ncpor')}
              </span>
              <span style={{ fontSize: 9, fontWeight: 700, background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe', padding: '1px 6px', borderRadius: 3 }}>
                MoES
              </span>
            </div>

            {/* Tier B: Main Application Brand Logo & Title */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, lineHeight: 1.2 }}>
              <img
                src="/himantar_logo.png"
                alt="HIMANTAR"
                style={{ height: 24, width: 'auto', objectFit: 'contain', display: 'block' }}
              />
              <span style={{ fontSize: 13.5, fontWeight: 800, color: '#0b3b60', letterSpacing: '-0.01em' }}>
                {t('app.title')}
              </span>
            </div>

            {/* Tier C: Subtitle */}
            <div style={{ fontSize: 10, fontWeight: 500, color: '#64748b', marginTop: 2, letterSpacing: '0.01em' }}>
              {t('app.subtitle')}
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
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              padding: '5px 12px',
            }}
          >
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: '#0b3b60', lineHeight: 1.1 }}>
                {user?.username ? user.username.toUpperCase() : 'OFFICER'}
              </div>
              <div style={{ fontSize: 9, fontWeight: 700, color: '#ea580c', letterSpacing: '0.04em' }}>
                {t('header.hq')}
              </div>
            </div>

            <button
              onClick={logout}
              style={{
                background: '#dc2626',
                border: 'none',
                color: '#ffffff',
                padding: '4px 8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                fontWeight: 800,
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


