import emblemOfIndia from '../../assets/emblem_of_india.svg'

interface StateEmblemProps {
  size?: number
  className?: string
  color?: string
}

export default function StateEmblem({
  size = 44,
  className = '',
}: StateEmblemProps) {
  return (
    <img
      src={emblemOfIndia}
      alt="Emblem Logo of India"
      className={className}
      style={{
        height: size,
        width: 'auto',
        maxHeight: size,
        objectFit: 'contain',
        display: 'inline-block',
        flexShrink: 0,
        filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.06))',
      }}
    />
  )
}
