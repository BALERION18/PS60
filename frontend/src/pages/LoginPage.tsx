import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useLanguage } from '../context/LanguageContext'
import GovtOfIndiaLogo from '../components/ui/GovtOfIndiaLogo'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { lang, toggleLang, t } = useLanguage()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [captchaInput, setCaptchaInput] = useState('7K9P2W')
  const [captchaCode, setCaptchaCode] = useState('7K9P2W')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function refreshCaptcha() {
    const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    let res = ''
    for (let i = 0; i < 6; i++) {
      res += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    setCaptchaCode(res)
    setCaptchaInput('')
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')

    // Basic captcha check
    if (captchaInput.trim().toUpperCase() !== captchaCode.toUpperCase()) {
      setError(lang === 'hi' ? 'गलत सुरक्षा कैप्चा कोड। कृपया पुनः प्रयास करें।' : 'Incorrect security captcha code. Please try again.')
      refreshCaptcha()
      return
    }

    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? (lang === 'hi' ? 'अमान्य अधिकारी क्रेडेंशियल्स। कृपया अधिकृत विवरण की जांच करें।' : 'Invalid officer credentials. Please verify your official ID.'))
    } finally {
      setLoading(false)
    }
  }

  function setQuickCreds(u: string, p: string) {
    setUsername(u)
    setPassword(p)
    setCaptchaInput(captchaCode)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#f0f4f8',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Inter, sans-serif',
      }}
    >
      {/* ── Tier 1: National Tricolour Ribbon ── */}
      <div className="tricolour-ribbon" />

      {/* ── Tier 2: Official Government Top Accessibility Bar ── */}
      <div
        style={{
          background: '#0b3b60',
          borderBottom: '2px solid #ff9933',
          padding: '8px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Mini Tricolour Flag */}
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

          <span style={{ fontSize: 12, fontWeight: 800, color: '#ffffff', letterSpacing: '0.02em' }}>
            {t('gov.title')}
          </span>
          <span style={{ color: '#93c5fd' }}>•</span>
          <span style={{ fontSize: 11.5, color: '#e0f2fe', fontWeight: 600 }}>
            {t('gov.ministry')}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 10.5, color: '#cbd5e1', fontWeight: 700 }} className="hidden sm:block">
            <span style={{ color: '#ffedd5', background: 'rgba(255, 153, 51, 0.25)', padding: '2px 8px', border: '1px solid #ff9933' }}>
              NIC MEGHRAJ SECURE GATEWAY
            </span>
          </div>

          {/* Language Switch Button */}
          <button
            onClick={toggleLang}
            style={{
              background: '#ffffff',
              border: '1px solid #ff9933',
              color: '#0b3b60',
              fontSize: 11,
              fontWeight: 800,
              padding: '3px 12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
            }}
            title={lang === 'hi' ? 'Switch portal to English' : 'पोर्टल को हिंदी में बदलें'}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#ea580c' }}>translate</span>
            <span>{lang === 'hi' ? 'English' : 'हिन्दी'}</span>
          </button>
        </div>
      </div>

      {/* ── Main SSO Login Area ── */}
      <main
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px 16px',
        }}
      >
        <div style={{ width: '100%', maxWidth: 480 }}>
          {/* Official Government of India Logo & Ministry Header */}
          <div style={{ textAlign: 'center', marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <GovtOfIndiaLogo size={56} color="#0b3b60" showGovtText={true} textColor="#0b3b60" />
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: '#0b3b60', letterSpacing: '0.04em' }}>
                {t('gov.ncpor')}
              </div>
              <h1 style={{ fontSize: 18, fontWeight: 900, color: '#0f172a', marginTop: 3, letterSpacing: '-0.01em' }}>
                {t('login.portal_title')}
              </h1>
              <div style={{ fontSize: 11, color: '#475569', fontWeight: 600 }}>
                {t('app.subtitle')}
              </div>
            </div>
          </div>

          {/* Institutional Government Card */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderTop: '4px solid #0b3b60',
              boxShadow: '0 4px 15px -1px rgba(0, 0, 0, 0.08), 0 2px 6px -2px rgba(0, 0, 0, 0.04)',
              padding: '24px 28px',
            }}
          >
            {/* Header with Classification Badge */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: '1px solid #e2e8f0',
                paddingBottom: 10,
                marginBottom: 14,
              }}
            >
              <div>
                <div style={{ fontSize: 14, fontWeight: 900, color: '#0b3b60', letterSpacing: '0.01em' }}>
                  {t('login.heading')}
                </div>
                <div style={{ fontSize: 10.5, color: '#64748b', fontWeight: 600 }}>
                  {t('login.restricted_notice')}
                </div>
              </div>
              <div
                style={{
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  padding: '3px 8px',
                  fontSize: 9,
                  fontWeight: 900,
                  color: '#dc2626',
                  letterSpacing: '0.04em',
                }}
              >
                {t('badge.restricted')}
              </div>
            </div>


            {error && (
              <div
                style={{
                  background: '#fef2f2',
                  border: '1px solid #f87171',
                  padding: '8px 12px',
                  marginBottom: 14,
                  fontSize: 11.5,
                  color: '#991b1b',
                  fontWeight: 600,
                }}
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {/* User ID */}
              <div style={{ marginBottom: 14 }}>
                <label
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: '0.03em',
                    color: '#334155',
                    display: 'block',
                    marginBottom: 5,
                  }}
                >
                  {t('login.username')}
                </label>
                <div style={{ position: 'relative' }}>
                  <span
                    className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2"
                    style={{ fontSize: 18, color: '#64748b' }}
                  >
                    badge
                  </span>
                  <input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    autoFocus
                    placeholder="admin / operator"
                    style={{
                      width: '100%',
                      background: '#f8fafc',
                      border: '1.5px solid #cbd5e1',
                      color: '#0f172a',
                      fontSize: 13,
                      fontFamily: 'Inter',
                      padding: '8px 10px 8px 36px',
                      outline: 'none',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = '#0b3b60')}
                    onBlur={(e) => (e.target.style.borderColor = '#cbd5e1')}
                  />
                </div>
              </div>

              {/* Password */}
              <div style={{ marginBottom: 14 }}>
                <label
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: '0.03em',
                    color: '#334155',
                    display: 'block',
                    marginBottom: 5,
                  }}
                >
                  {t('login.password')}
                </label>
                <div style={{ position: 'relative' }}>
                  <span
                    className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2"
                    style={{ fontSize: 18, color: '#64748b' }}
                  >
                    lock
                  </span>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="••••••••••••"
                    style={{
                      width: '100%',
                      background: '#f8fafc',
                      border: '1.5px solid #cbd5e1',
                      color: '#0f172a',
                      fontSize: 13,
                      fontFamily: 'Inter',
                      padding: '8px 10px 8px 36px',
                      outline: 'none',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = '#0b3b60')}
                    onBlur={(e) => (e.target.style.borderColor = '#cbd5e1')}
                  />
                </div>
              </div>

              {/* Security Captcha Challenge (Iconic Indian Government Feature) */}
              <div style={{ marginBottom: 18 }}>
                <label
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: '0.03em',
                    color: '#334155',
                    display: 'block',
                    marginBottom: 5,
                  }}
                >
                  {t('login.captcha')}
                </label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    value={captchaInput}
                    onChange={(e) => setCaptchaInput(e.target.value)}
                    required
                    placeholder="Captcha Code"
                    style={{
                      flex: 1,
                      background: '#f8fafc',
                      border: '1.5px solid #cbd5e1',
                      color: '#0f172a',
                      fontSize: 13,
                      fontFamily: 'Inter',
                      padding: '8px 12px',
                      outline: 'none',
                      textTransform: 'uppercase',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = '#0b3b60')}
                    onBlur={(e) => (e.target.style.borderColor = '#cbd5e1')}
                  />

                  {/* Stylized Captcha Canvas Box */}
                  <div
                    style={{
                      background: '#e0f2fe',
                      border: '1px solid #7dd3fc',
                      padding: '5px 12px',
                      fontFamily: 'Courier New, monospace',
                      fontSize: 18,
                      fontWeight: 900,
                      letterSpacing: '4px',
                      color: '#0369a1',
                      userSelect: 'none',
                      textDecoration: 'line-through',
                      fontStyle: 'italic',
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    {captchaCode}
                  </div>

                  {/* Captcha Refresh Button */}
                  <button
                    type="button"
                    onClick={refreshCaptcha}
                    style={{
                      background: '#f1f5f9',
                      border: '1px solid #cbd5e1',
                      color: '#475569',
                      padding: '7px 8px',
                      cursor: 'pointer',
                    }}
                    title="Refresh Captcha"
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>refresh</span>
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  background: loading ? '#64748b' : '#0b3b60',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: 12.5,
                  fontWeight: 800,
                  letterSpacing: '0.05em',
                  padding: '11px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontFamily: 'Inter',
                  textTransform: 'uppercase',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  boxShadow: '0 2px 4px rgba(11, 59, 96, 0.25)',
                  transition: 'background 0.15s',
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#ff9933' }}>
                  verified_user
                </span>
                <span>{loading ? t('login.authenticating') : t('login.button')}</span>
              </button>
            </form>

            {/* Quick Test Credentials Helper */}
            <div
              style={{
                marginTop: 16,
                paddingTop: 14,
                borderTop: '1px solid #e2e8f0',
                fontSize: 10.5,
                color: '#64748b',
              }}
            >
              <div style={{ fontWeight: 700, color: '#334155', marginBottom: 6 }}>
                {t('login.dev_helper')}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  onClick={() => setQuickCreds('admin', 'admin123')}
                  style={{
                    flex: 1,
                    background: '#f8fafc',
                    border: '1px solid #cbd5e1',
                    color: '#0b3b60',
                    padding: '6px 8px',
                    fontSize: 10,
                    cursor: 'pointer',
                    fontFamily: 'Inter',
                    textAlign: 'left',
                    fontWeight: 700,
                  }}
                  onMouseOver={(e) => ((e.currentTarget as HTMLElement).style.borderColor = '#0b3b60')}
                  onMouseOut={(e) => ((e.currentTarget as HTMLElement).style.borderColor = '#cbd5e1')}
                >
                  <span style={{ fontWeight: 800, color: '#ea580c' }}>Admin:</span> admin / admin123
                </button>
              </div>
            </div>
          </div>

          {/* National Accreditation Footnote */}
          <div
            style={{
              marginTop: 16,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 14,
              fontSize: 10,
              color: '#64748b',
              fontWeight: 800,
              letterSpacing: '0.04em',
            }}
          >
            <span>DIGITAL INDIA</span>
            <span>•</span>
            <span>GIGW 3.0 COMPLIANT</span>
            <span>•</span>
            <span>NIC SECURE INFRASTRUCTURE</span>
          </div>
        </div>
      </main>

      {/* ── Tier 3: National Tricolour Ribbon at bottom ── */}
      <div className="tricolour-bottom" />
    </div>
  )
}
