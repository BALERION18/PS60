import emblemOfIndia from '../../assets/emblem_of_india.svg'

interface GovtOfIndiaLogoProps {
  size?: number
  className?: string
  color?: string
  showGovtText?: boolean
  textColor?: string
}

export default function GovtOfIndiaLogo({
  size = 50,
  className = '',
  showGovtText = true,
  textColor = '#0b3b60',
}: GovtOfIndiaLogoProps) {
  return (
    <div
      className={`inline-flex items-center gap-3 ${className}`}
      style={{ flexShrink: 0, userSelect: 'none' }}
      title="Government of India | भारत सरकार"
    >
      {/* Official High-Resolution Emblem Logo of India Image */}
      <img
        src={emblemOfIndia}
        alt="Emblem Logo of India"
        style={{
          height: size,
          width: 'auto',
          maxHeight: size,
          objectFit: 'contain',
          display: 'block',
          flexShrink: 0,
          filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.08))',
        }}
      />

      {/* Official Government of India Text Lockup */}
      {showGovtText && (
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
          <span
            style={{
              fontSize: 12.5,
              fontWeight: 800,
              color: textColor,
              letterSpacing: '0.02em',
              fontFamily: 'Inter, sans-serif',
            }}
          >
            भारत सरकार
          </span>
          <span
            style={{
              fontSize: 10,
              fontWeight: 800,
              color: textColor,
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              fontFamily: 'Inter, sans-serif',
              marginTop: 1,
            }}
          >
            GOVERNMENT OF INDIA
          </span>
        </div>
      )}
    </div>
  )
}
