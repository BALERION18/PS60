/**
 * PageSection — reusable collapsible accordion section for all pages.
 *
 * Usage:
 *   const [open, setOpen] = useState(true)
 *   <PageSection icon="bolt" title="ENERGY KPIs" open={open} onToggle={() => setOpen(v => !v)}>
 *     ...content...
 *   </PageSection>
 */
import type { ReactNode } from 'react'

interface PageSectionProps {
  icon: string
  title: string
  badge?: string
  badgeColor?: string
  accentColor?: string
  open: boolean
  onToggle: () => void
  children: ReactNode
  /** Extra padding inside the body. Default: 10px */
  bodyPadding?: number | string
  /** Body background. Default: #F6F3ED */
  bodyBg?: string
}

export default function PageSection({
  icon,
  title,
  badge,
  badgeColor = '#6F8747',
  accentColor = '#4F5935',
  open,
  onToggle,
  children,
  bodyPadding = 10,
  bodyBg = '#F6F3ED',
}: PageSectionProps) {
  return (
    <div style={{ marginBottom: 10 }}>
      {/* ── Header ── */}
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '7px 13px',
          background: open ? '#F6F3ED' : '#FCFBF8',
          border: '1px solid #DDD8CC',
          borderLeft: `3px solid ${accentColor}`,
          cursor: 'pointer',
          fontFamily: 'Inter',
          borderRadius: open ? '7px 7px 0 0' : 7,
          transition: 'background 0.15s',
          textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 15, color: accentColor, flexShrink: 0 }}
          >
            {icon}
          </span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 800,
              color: '#252820',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
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
                marginLeft: 2,
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
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            flexShrink: 0,
          }}
        >
          expand_more
        </span>
      </button>

      {/* ── Body ── */}
      {open && (
        <div
          style={{
            border: '1px solid #DDD8CC',
            borderTop: 'none',
            borderRadius: '0 0 7px 7px',
            background: bodyBg,
            padding: bodyPadding,
          }}
        >
          {children}
        </div>
      )}
    </div>
  )
}
