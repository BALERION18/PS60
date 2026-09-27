import { useState, useRef } from 'react'

interface Props {
  stationId: string
}

export interface HotspotPart {
  id: string
  name: string
  simpleTag: string
  box: { left: number; top: number; width: number; height: number }
  pin: { x: number; y: number }
  status: 'Normal' | 'Running' | 'Online' | 'Active'
  statusColor: string
  about: string
  stats: Array<{ label: string; value: string; note?: string; good?: boolean }>
}

const MAITRI_PARTS: HotspotPart[] = [
  {
    id: 'cmd_hub',
    name: 'Main Office & Command Hub',
    simpleTag: 'Central Base',
    box: { left: 43.5, top: 38.5, width: 17, height: 26 },
    pin: { x: 52, y: 51 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'Central expedition office, radio room, and emergency safety control.',
    stats: [
      { label: 'Inside Temp', value: '+21.4°C', note: 'Warm & comfortable', good: true },
      { label: 'People Inside', value: '14 crew', note: 'On-duty', good: true },
      { label: 'Safety Alarms', value: '100% Safe', note: 'All systems armed', good: true },
      { label: 'Building Health', value: 'Good', note: 'Solid foundations', good: true },
    ],
  },
  {
    id: 'habitat_a',
    name: 'Living Rooms & Medical Clinic',
    simpleTag: 'Crew Quarters',
    box: { left: 20.5, top: 51, width: 18.5, height: 32 },
    pin: { x: 29.5, y: 67 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'Heated bedrooms for 25 scientists, doctor clinic, and the Indian Flag.',
    stats: [
      { label: 'Room Temp', value: '+22.0°C', note: 'Heated', good: true },
      { label: 'Fresh Air (CO₂)', value: 'Fresh (420 ppm)', note: 'Clean air', good: true },
      { label: 'Hot Water', value: '+48.5°C', note: 'Running 24/7', good: true },
      { label: 'Beds Occupied', value: '18 of 25 beds', note: '7 spare beds' },
    ],
  },
  {
    id: 'power_plant',
    name: 'Power Generators (DG-1, 2, 3)',
    simpleTag: 'Electricity',
    box: { left: 12, top: 34, width: 21, height: 22 },
    pin: { x: 22.5, y: 45 },
    status: 'Running',
    statusColor: '#ea580c',
    about: 'Diesel generator sheds that produce round-the-clock electricity.',
    stats: [
      { label: 'Power Produced', value: '84 kW', note: 'Running normal', good: true },
      { label: 'Fuel Consumed', value: '16.4 L / hour', note: 'Normal burn rate' },
      { label: 'Backup Engine', value: 'Ready', note: 'Auto switch on standby', good: true },
      { label: 'Engine Health', value: 'Healthy', note: 'Oil & temp normal', good: true },
    ],
  },
  {
    id: 'fuel_farm',
    name: 'Fuel Tanks (Winter Diesel)',
    simpleTag: 'Fuel Storage',
    box: { left: 75.5, top: 19, width: 18.5, height: 34 },
    pin: { x: 84.5, y: 36 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'Insulated steel tanks storing special polar fuel that never freezes.',
    stats: [
      { label: 'Fuel Left', value: '142,500 Litres', note: '81% full', good: true },
      { label: 'Days Remaining', value: '214 Days', note: 'Safe till next ship', good: true },
      { label: 'Tank Heating', value: 'Active (-2.4°C)', note: 'Stops fuel freezing', good: true },
      { label: 'Leak Check', value: 'Zero Leaks', note: '100% safe', good: true },
    ],
  },
  {
    id: 'vsat_comms',
    name: 'Satellite Dish & Internet Link',
    simpleTag: 'Communication',
    box: { left: 45.5, top: 2, width: 13.5, height: 38 },
    pin: { x: 52, y: 21 },
    status: 'Online',
    statusColor: '#16a34a',
    about: 'Satellite dish connecting Maitri directly to NCPOR headquarters in Goa.',
    stats: [
      { label: 'Satellite Link', value: 'Online', note: 'ISRO GSAT-30 satellite', good: true },
      { label: 'Signal Strength', value: 'Strong (+14 dB)', note: 'Clear sky', good: true },
      { label: 'Data Compression', value: '93% Saved', note: 'VajraX Protobuf speed', good: true },
      { label: 'Snow De-icer', value: 'Heating On', note: 'Dish clear of ice', good: true },
    ],
  },
  {
    id: 'met_mast',
    name: 'Weather Station Tower',
    simpleTag: 'Weather & Wind',
    box: { left: 17, top: 18, width: 5.5, height: 62 },
    pin: { x: 19.5, y: 49 },
    status: 'Active',
    statusColor: '#0284c7',
    about: '10-meter tower measuring polar winds, freezing temperatures, and blizzards.',
    stats: [
      { label: 'Wind Speed', value: '63 km/h', note: 'Fresh breeze' },
      { label: 'Outside Temp', value: '-18.4°C', note: 'Very Cold' },
      { label: 'Wind Chill', value: '-29°C', note: 'Wear polar jackets' },
      { label: 'Blizzard Warning', value: 'Low Risk', note: 'Clear visibility', good: true },
    ],
  },
  {
    id: 'east_wing',
    name: 'Dining Hall, Kitchen & Workshop',
    simpleTag: 'Kitchen & Repair',
    box: { left: 56.5, top: 28, width: 25.5, height: 29 },
    pin: { x: 69, y: 42 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'Crew dining room, fresh water snow-melter, and mechanical repair shop.',
    stats: [
      { label: 'Drinking Water', value: '9,200 Litres', note: 'Clean melted ice', good: true },
      { label: 'Food Ration', value: '180 Days left', note: 'Plenty in storage', good: true },
      { label: 'Heating Warmth', value: '+48°C water', note: 'Reuses engine heat', good: true },
      { label: 'Fire Safety', value: 'Safe', note: 'Sensors active', good: true },
    ],
  },
  {
    id: 'science_lab',
    name: 'Science & Physics Labs',
    simpleTag: 'Research',
    box: { left: 35, top: 35, width: 15, height: 20 },
    pin: { x: 42.5, y: 45 },
    status: 'Active',
    statusColor: '#16a34a',
    about: 'Scientific equipment studying polar auroras, ozone layer, and earth magnetism.',
    stats: [
      { label: 'Instruments', value: 'All Working', note: 'Clean power supply', good: true },
      { label: 'Earth Magnetism', value: 'Normal (Quiet)', note: 'Steady signal', good: true },
      { label: 'Ground Shaking', value: 'Quiet (<0.01 mm/s)', note: 'No tremors', good: true },
      { label: 'Data Sync', value: 'Continuous', note: 'Live to India labs', good: true },
    ],
  },
  {
    id: 'snow_melt',
    name: 'Underground Ground Heating',
    simpleTag: 'Foundation Care',
    box: { left: 38.5, top: 73, width: 10.5, height: 17 },
    pin: { x: 43.5, y: 81 },
    status: 'Active',
    statusColor: '#16a34a',
    about: 'Pumps warm fluid under the pillars so frozen ice does not harm foundations.',
    stats: [
      { label: 'Water Pump Flow', value: '42 Litres / min', note: 'Circulating smooth', good: true },
      { label: 'Water Temp', value: '+35°C', note: 'Warm water loop', good: true },
      { label: 'Ice on Pillars', value: 'Zero ice (0 mm)', note: 'Clean & safe', good: true },
      { label: 'Pumps Status', value: 'Running', note: 'Automatic', good: true },
    ],
  },
]

const BHARATI_PARTS: HotspotPart[] = [
  {
    id: 'bhr_entrance',
    name: 'Main Base Entrance & Airlock',
    simpleTag: 'Main Entrance',
    box: { left: 45.0, top: 38.0, width: 14.0, height: 35.0 },
    pin: { x: 52, y: 52 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'Heated central airlock, entrance stairs, and expedition management offices.',
    stats: [
      { label: 'Inside Temp', value: '+20.8°C', note: 'Warm & regulated', good: true },
      { label: 'Station Crew', value: '22 scientists', note: 'Living on-site', good: true },
      { label: 'Structure Health', value: '100% Nominal', note: 'Aerodynamic steel', good: true },
      { label: 'Air Pressure', value: '1,014 hPa', note: 'Normal sealed air', good: true },
    ],
  },
  {
    id: 'bhr_habitat',
    name: 'Living Rooms & Medical ICU (Left Wing)',
    simpleTag: 'Living Quarters',
    box: { left: 18.0, top: 47.0, width: 30.0, height: 32.0 },
    pin: { x: 34, y: 60 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'Modern living quarters for 47 crew members, surgery room, and the Indian Flag.',
    stats: [
      { label: 'Bedroom Temp', value: '+21.5°C', note: 'Thermostat heated', good: true },
      { label: 'Fresh Air (CO₂)', value: 'Fresh (410 ppm)', note: 'Continuous filtered', good: true },
      { label: 'Beds Occupied', value: '22 of 47 beds', note: '25 spare berths' },
      { label: 'Fire Safety', value: '100% Safe', note: 'Automated fog mist', good: true },
    ],
  },
  {
    id: 'bhr_lounge',
    name: 'Dining Mess & Panoramic Lounge (Right Wing)',
    simpleTag: 'Dining & Lounge',
    box: { left: 54.0, top: 49.0, width: 28.0, height: 27.0 },
    pin: { x: 68, y: 58 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'Dining hall and triple-glazed panoramic lounge looking out over Prydz Bay ocean.',
    stats: [
      { label: 'Lounge Temp', value: '+21.0°C', note: 'Heated ocean view', good: true },
      { label: 'Drinking Water', value: '14,000 Litres', note: 'Desalinated clean water', good: true },
      { label: 'Food Ration', value: '240 Days left', note: 'Ample nutrition storage', good: true },
      { label: 'Window Heaters', value: 'Active', note: 'Zero frost on glass', good: true },
    ],
  },
  {
    id: 'bhr_labs',
    name: 'Ocean & Atmospheric Science Labs',
    simpleTag: 'Science Labs',
    box: { left: 30.0, top: 38.0, width: 44.0, height: 16.0 },
    pin: { x: 44, y: 44 },
    status: 'Active',
    statusColor: '#16a34a',
    about: 'Specialized laboratories studying polar marine biology, glaciology, and atmosphere.',
    stats: [
      { label: 'Instruments', value: 'All Online', note: 'Clean power bus', good: true },
      { label: 'Seismic Wave', value: '< 0.02 mm/s', note: 'Ultra-quiet bedrock', good: true },
      { label: 'Ocean Sensor', value: 'Active Probe', note: 'Prydz Bay sea data', good: true },
      { label: 'Data Relay', value: 'Live to Goa', note: 'Continuous feed', good: true },
    ],
  },
  {
    id: 'bhr_fuel',
    name: 'Bulk Fuel Silos (Winter Arctic Fuel)',
    simpleTag: 'Fuel Tanks',
    box: { left: 73.0, top: 31.0, width: 16.0, height: 26.0 },
    pin: { x: 81, y: 42 },
    status: 'Normal',
    statusColor: '#16a34a',
    about: 'High-grade stainless steel fuel silos holding freeze-proof polar fuel.',
    stats: [
      { label: 'Fuel Reserve', value: '185,000 Litres', note: '78% capacity', good: true },
      { label: 'Days Remaining', value: '280 Days', note: 'Safe till next ship', good: true },
      { label: 'Fuel Core Temp', value: '-1.5°C', note: 'Trace heated', good: true },
      { label: 'Leak Sensors', value: 'Zero Leaks', note: 'Environment safe', good: true },
    ],
  },
  {
    id: 'bhr_satellite',
    name: 'High-Speed Satellite Towers (GSAT-30)',
    simpleTag: 'Satellite Link',
    box: { left: 47.0, top: 15.0, width: 12.0, height: 28.0 },
    pin: { x: 54, y: 27 },
    status: 'Online',
    statusColor: '#16a34a',
    about: 'Dedicated high-speed satellite dish masts linking Bharati to NCPOR Goa.',
    stats: [
      { label: 'Satellite Link', value: 'Online (Fast)', note: 'Ku-Band dish active', good: true },
      { label: 'Signal Strength', value: 'Strong (+16 dB)', note: 'Clear sky margin', good: true },
      { label: 'Bandwidth Saved', value: '94% Saved', note: 'VajraX Protobuf speed', good: true },
      { label: 'ISRO Tracking', value: 'Connected', note: 'GSAT-30 relay', good: true },
    ],
  },
  {
    id: 'bhr_metmast',
    name: 'Weather & Wind Mast',
    simpleTag: 'Weather Mast',
    box: { left: 18.0, top: 16.0, width: 6.0, height: 38.0 },
    pin: { x: 21, y: 33 },
    status: 'Active',
    statusColor: '#0284c7',
    about: 'Tower measuring polar coastal winds, temperatures, blizzards, and sea fog.',
    stats: [
      { label: 'Wind Velocity', value: '44 km/h', note: 'Moderate breeze' },
      { label: 'Outside Temp', value: '-12.1°C', note: 'Coastal Antarctic cold' },
      { label: 'Air Humidity', value: '65%', note: 'Oceanic air' },
      { label: 'Blizzard Alert', value: 'Clear / Safe', note: 'Good visibility', good: true },
    ],
  },
  {
    id: 'bhr_snowcat',
    name: 'PistenBully Snow Vehicle & Crew',
    simpleTag: 'Expedition Crew',
    box: { left: 58.0, top: 70.0, width: 12.0, height: 16.0 },
    pin: { x: 64, y: 76 },
    status: 'Active',
    statusColor: '#ea580c',
    about: 'Heavy-tracked snowcat polar vehicle and expedition crew on the ground.',
    stats: [
      { label: 'Vehicle Engine', value: 'Running', note: 'Heated cabin', good: true },
      { label: 'Crew Outside', value: '4 Scientists', note: 'Polar suits equipped', good: true },
      { label: 'GPS Sync', value: 'Active', note: 'Satellite tracking', good: true },
      { label: 'Mission', value: 'Field Survey', note: 'Nominal operation', good: true },
    ],
  },
  {
    id: 'bhr_ocean',
    name: 'Prydz Bay Ocean & Coastal Ice Shelf',
    simpleTag: 'Prydz Bay Ocean',
    box: { left: 57.0, top: 24.0, width: 33.0, height: 12.0 },
    pin: { x: 74, y: 29 },
    status: 'Active',
    statusColor: '#0284c7',
    about: 'Antarctic Southern Ocean waters monitored for ice shelf stability and marine ecology.',
    stats: [
      { label: 'Sea Water Temp', value: '-1.8°C', note: 'Near freezing point' },
      { label: 'Ice Pack Extent', value: '4.2 km offshore', note: 'Stable sea ice', good: true },
      { label: 'Tide Height', value: '0.8 m', note: 'Normal ocean tide', good: true },
      { label: 'Water Salinity', value: '34.1 PSU', note: 'Typical polar sea', good: true },
    ],
  },
]

export default function SchematicPanel({ stationId }: Props) {
  const [hoveredPartId, setHoveredPartId] = useState<string | null>(null)
  const [selectedPartId, setSelectedPartId] = useState<string | null>(null)
  const [showAllPins, setShowAllPins] = useState<boolean>(true)
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const isMaitri = stationId === 'maitri'
  const activePartsList = isMaitri ? MAITRI_PARTS : BHARATI_PARTS
  const activePartId = selectedPartId || hoveredPartId
  const activePart = activePartsList.find((p) => p.id === activePartId) ?? null

  const handleSelectPart = (id: string) => {
    setSelectedPartId((curr) => (curr === id ? null : id))
  }

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 380,
        overflow: 'hidden',
        ...(isFullscreen
          ? {
              position: 'fixed',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              zIndex: 9999,
            }
          : {}),
      }}
    >


      {/* ── Easy-to-Understand Subsystems Filter Bar ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 8px',
          background: '#f8fafc',
          borderBottom: '1px solid #cbd5e1',
          overflowX: 'auto',
          whiteSpace: 'nowrap',
        }}
      >
        <span style={{ fontSize: 9.5, fontWeight: 800, color: '#0b3b60', textTransform: 'uppercase', marginRight: 4 }}>
          Buildings:
        </span>

        {activePartsList.map((part) => {
          const isHovered = hoveredPartId === part.id
          const isSelected = selectedPartId === part.id
          return (
            <button
              key={part.id}
              onMouseEnter={() => setHoveredPartId(part.id)}
              onMouseLeave={() => setHoveredPartId(null)}
              onClick={() => handleSelectPart(part.id)}
              style={{
                background: isSelected ? '#0b3b60' : isHovered ? '#f1f5f9' : '#ffffff',
                color: isSelected ? '#ffffff' : isHovered ? '#0b3b60' : '#334155',
                border: isSelected ? '1px solid #0b3b60' : '1px solid #cbd5e1',
                borderBottom: isSelected ? '2px solid #ff9933' : '1px solid #cbd5e1',
                padding: '3px 7px',
                fontSize: 10,
                fontWeight: isSelected ? 800 : 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                borderRadius: 2,
              }}
            >
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: isSelected ? '#ff9933' : '#15803d' }} />
              <span>{part.simpleTag}</span>
            </button>
          )
        })}

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5 }}>
          {selectedPartId && (
            <button
              onClick={() => setSelectedPartId(null)}
              style={{
                background: '#fee2e2',
                color: '#991b1b',
                border: '1px solid #fca5a5',
                padding: '3px 8px',
                fontSize: 10,
                fontWeight: 800,
                cursor: 'pointer',
              }}
            >
              Reset
            </button>
          )}

          <button
            onClick={() => setShowAllPins((v) => !v)}
            title="Toggle pin markers"
            style={{
              background: showAllPins ? '#e0f2fe' : '#ffffff',
              border: showAllPins ? '1px solid #0284c7' : '1px solid #cbd5e1',
              color: showAllPins ? '#0369a1' : '#64748b',
              padding: '3px 7px',
              fontSize: 10,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 3,
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 13 }}>
              {showAllPins ? 'visibility' : 'visibility_off'}
            </span>
            <span>{showAllPins ? 'Markers' : 'Hidden'}</span>
          </button>

          <button
            onClick={() => setIsFullscreen((v) => !v)}
            title={isFullscreen ? 'Exit Full Screen' : 'Full Screen'}
            style={{
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              color: '#334155',
              padding: '3px 7px',
              fontSize: 10,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 3,
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 13 }}>
              {isFullscreen ? 'fullscreen_exit' : 'fullscreen'}
            </span>
            <span>{isFullscreen ? 'Exit' : 'Full'}</span>
          </button>
        </div>
      </div>

      {/* ── Aerial Image Canvas ── */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          background: '#0f172a',
          overflow: 'hidden',
          minHeight: 320,
          display: 'flex',
        }}
      >
        <img
          src={isMaitri ? '/maitri_station.jpg' : '/bharati_station.jpg'}
          alt={`${stationId} aerial digital twin view`}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center 42%',
            display: 'block',
          }}
          loading="eager"
        />

        {/* ── Interactive Bounding Boxes ── */}
        {activePartsList.map((part) => {
          const isHovered = hoveredPartId === part.id
          const isSelected = selectedPartId === part.id
          const isActive = isHovered || isSelected

          return (
            <div
              key={part.id}
              onMouseEnter={() => setHoveredPartId(part.id)}
              onMouseLeave={() => setHoveredPartId(null)}
              onClick={() => handleSelectPart(part.id)}
              title={`Click to view ${part.name}`}
              style={{
                position: 'absolute',
                left: `${part.box.left}%`,
                top: `${part.box.top}%`,
                width: `${part.box.width}%`,
                height: `${part.box.height}%`,
                cursor: 'pointer',
                zIndex: isActive ? 30 : 20,
                transition: 'all 0.15s ease',
              }}
            >
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  border: isActive ? '2px solid #ff9933' : '1px dashed transparent',
                  background: isActive ? 'rgba(11, 59, 96, 0.35)' : 'transparent',
                  boxShadow: isActive ? '0 0 14px rgba(255, 153, 51, 0.7), inset 0 0 10px rgba(255, 153, 51, 0.25)' : 'none',
                  position: 'relative',
                  borderRadius: 2,
                }}
              >
                {isActive && (
                  <div
                    style={{
                      position: 'absolute',
                      top: -18,
                      left: 0,
                      background: '#0b3b60',
                      color: '#ffffff',
                      fontSize: 9.5,
                      fontWeight: 800,
                      padding: '1px 6px',
                      whiteSpace: 'nowrap',
                      borderLeft: '2px solid #ff9933',
                    }}
                  >
                    {part.simpleTag}
                  </div>
                )}
              </div>
            </div>
          )
        })}

        {/* ── Visual Pins on the Station ── */}
        {showAllPins &&
          activePartsList.map((part) => {
            const isHovered = hoveredPartId === part.id
            const isSelected = selectedPartId === part.id
            const isActive = isHovered || isSelected

            return (
              <div
                key={`pin-${part.id}`}
                onMouseEnter={() => setHoveredPartId(part.id)}
                onMouseLeave={() => setHoveredPartId(null)}
                onClick={() => handleSelectPart(part.id)}
                style={{
                  position: 'absolute',
                  left: `${part.pin.x}%`,
                  top: `${part.pin.y}%`,
                  transform: 'translate(-50%, -50%)',
                  zIndex: isActive ? 35 : 22,
                  cursor: 'pointer',
                }}
              >
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span
                    className="pulse-dot"
                    style={{
                      position: 'absolute',
                      width: isActive ? 22 : 18,
                      height: isActive ? 22 : 18,
                      borderRadius: '50%',
                      background: '#38bdf8',
                      opacity: isActive ? 0.85 : 0.45,
                    }}
                  />
                  <div
                    style={{
                      width: isActive ? 14 : 11,
                      height: isActive ? 14 : 11,
                      borderRadius: '50%',
                      background: '#38bdf8',
                      border: '2px solid #ffffff',
                      boxShadow: '0 2px 5px rgba(0,0,0,0.35)',
                    }}
                  />
                </div>
              </div>
            )
          })}

        {/* ── Minimal, Clean & Easy-to-Understand Hover Card ── */}
        {activePart && (
          <div
            style={{
              position: 'absolute',
              right: activePart.pin.x > 60 ? `${100 - activePart.box.left + 2}%` : 'auto',
              left: activePart.pin.x <= 60 ? `${activePart.box.left + activePart.box.width + 1.5}%` : 'auto',
              top: `${Math.max(6, Math.min(48, activePart.box.top - 4))}%`,
              zIndex: 45,
              width: 255,
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderLeft: '4px solid #ff9933',
              boxShadow: '0 6px 18px rgba(11, 59, 96, 0.16)',
              color: '#0f172a',
              pointerEvents: selectedPartId ? 'auto' : 'none',
              padding: '10px 12px',
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: 9.5, fontWeight: 800, color: '#ff9933', textTransform: 'uppercase' }}>
                {activePart.simpleTag}
              </span>
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 800,
                  color: '#15803d',
                  background: '#f0fdf4',
                  padding: '1px 5px',
                  border: '1px solid #bbf7d0',
                }}
              >
                ● {activePart.status}
              </span>
            </div>

            {/* Simple Title */}
            <div style={{ fontSize: 12.5, fontWeight: 900, color: '#0b3b60', lineHeight: 1.2, marginBottom: 4 }}>
              {activePart.name}
            </div>

            {/* Easy one-line explanation */}
            <div style={{ fontSize: 10.5, color: '#475569', lineHeight: 1.35, marginBottom: 8 }}>
              {activePart.about}
            </div>

            {/* 4 Clean Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 5 }}>
              {activePart.stats.map((s, i) => (
                <div
                  key={i}
                  style={{
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    padding: '4px 6px',
                  }}
                >
                  <div style={{ fontSize: 9, color: '#64748b' }}>{s.label}</div>
                  <div style={{ fontSize: 11.5, fontWeight: 800, color: '#0f172a', marginTop: 1 }}>{s.value}</div>
                  {s.note && (
                    <div style={{ fontSize: 8.5, color: s.good ? '#15803d' : '#64748b', fontWeight: 600 }}>
                      {s.note}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {selectedPartId && (
              <div style={{ marginTop: 8, textAlign: 'right' }}>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setSelectedPartId(null)
                  }}
                  style={{
                    background: '#f1f5f9',
                    border: '1px solid #cbd5e1',
                    color: '#475569',
                    fontSize: 9.5,
                    fontWeight: 700,
                    padding: '2px 6px',
                    cursor: 'pointer',
                  }}
                >
                  ✕ Close
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Bottom Subtle Legend ── */}
        <div
          style={{
            position: 'absolute',
            bottom: 6,
            left: 8,
            zIndex: 15,
            background: 'rgba(255, 255, 255, 0.94)',
            border: '1px solid #cbd5e1',
            borderLeft: '3px solid #138808',
            padding: '2px 8px',
            fontSize: 9,
            fontWeight: 800,
            color: '#0b3b60',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span style={{ color: '#138808' }}>●</span>
          <span>
            {isMaitri
              ? 'Maitri Station, Antarctica (70°S, 11°E) • Hover on any building to view info'
              : 'Bharati Station, Larsemann Hills (69°S, 76°E) • Hover on any building to view info'}
          </span>
        </div>
      </div>

      {/* ── Bottom Clean Details (When a Part is Clicked) ── */}
      {selectedPartId && activePart && (
        <div
          style={{
            padding: '10px 14px',
            background: '#ffffff',
            borderTop: '2px solid #ff9933',
            color: '#0f172a',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ background: '#0b3b60', color: '#ffffff', fontSize: 9, fontWeight: 800, padding: '1px 6px' }}>
                {activePart.simpleTag}
              </span>
              <span style={{ fontSize: 12.5, fontWeight: 900, color: '#0b3b60' }}>{activePart.name}</span>
              <span style={{ fontSize: 10, color: '#15803d', fontWeight: 700 }}>● {activePart.status}</span>
            </div>
            <button
              onClick={() => setSelectedPartId(null)}
              style={{
                background: 'none',
                border: 'none',
                color: '#64748b',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              ✕ Close
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
            {activePart.stats.map((s, i) => (
              <div key={i} style={{ background: '#f8fafc', padding: '6px 10px', border: '1px solid #e2e8f0', borderLeft: '3px solid #0b3b60' }}>
                <div style={{ fontSize: 9, color: '#64748b' }}>{s.label}</div>
                <div style={{ fontSize: 13, fontWeight: 900, color: '#0f172a', marginTop: 1 }}>{s.value}</div>
                {s.note && <div style={{ fontSize: 8.5, color: '#15803d', fontWeight: 600 }}>{s.note}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
