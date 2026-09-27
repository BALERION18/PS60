import React, { createContext, useContext, useState, useEffect } from 'react'

export type Language = 'en' | 'hi'

export interface Translations {
  [key: string]: {
    en: string
    hi: string
  }
}

export const DICTIONARY: Translations = {
  // Top Header & Accessibility
  'gov.title': { en: 'Government of India', hi: 'भारत सरकार' },
  'gov.ministry': { en: 'Ministry of Earth Sciences', hi: 'पृथ्वी विज्ञान मंत्रालय' },
  'gov.ncpor': { en: 'National Centre for Polar and Ocean Research (NCPOR)', hi: 'राष्ट्रीय ध्रुवीय एवं समुद्री अनुसंधान केंद्र (एनसीपीओआर)' },
  'gov.ncpor_short': { en: 'NCPOR, Goa', hi: 'एनसीपीओआर, गोवा' },
  'app.name': { en: 'HIMANTAR', hi: 'हिमांतर' },
  'app.title': { en: 'Antarctic Digital Twin & Telemetry Command', hi: 'अंटार्कटिक डिजिटल ट्विन एवं टेलीमेट्री नियंत्रण' },
  'app.subtitle': { en: 'Remote Management Platform (Maitri & Bharati) • Ministry of Earth Sciences, Govt. of India', hi: 'रिमोट प्रबंधन प्रणाली (मैत्री एवं भारती) • पृथ्वी विज्ञान मंत्रालय, भारत सरकार' },
  'badge.restricted': { en: 'RESTRICTED / OFFICIAL USE ONLY', hi: 'प्रतिबंधित / केवल आधिकारिक उपयोग हेतु' },
  'badge.govt': { en: 'GOVT. OF INDIA', hi: 'भारत सरकार' },
  'header.stations_online': { en: 'Stations Online', hi: 'सक्रिय स्टेशन' },
  'header.normal': { en: 'NORMAL', hi: 'सामान्य' },
  'header.critical': { en: 'CRITICAL', hi: 'अति गंभीर' },
  'header.search': { en: 'Search telemetry, sensors, reports...', hi: 'टेलीमेट्री, सेंसर, रिपोर्ट खोजें...' },
  'header.search_btn': { en: 'Search', hi: 'खोजें' },
  'header.logout': { en: 'LOGOUT', hi: 'लॉगआउट' },
  'header.hq': { en: 'NCPOR HQ | GOA', hi: 'एनसीपीओआर मुख्यालय | गोवा' },
  'header.skip_main': { en: 'Skip to Main Content', hi: 'मुख्य विषयवस्तु में जाएं' },
  'header.screen_reader': { en: 'Screen Reader Access', hi: 'स्क्रीन रीडर एक्सेस' },
  'header.text_size': { en: 'Text Size', hi: 'फ़ॉन्ट आकार' },
  'header.contrast': { en: 'Standard / High Contrast', hi: 'मानक / उच्च कंट्रास्ट' },
  'header.national_portal': { en: 'National Portal of India', hi: 'भारत का राष्ट्रीय पोर्टल' },

  // Nav Bar Tabs
  'topnav.home': { en: 'Home', hi: 'मुख्य पृष्ठ' },
  'topnav.maitri': { en: 'Maitri Base', hi: 'मैत्री स्टेशन' },
  'topnav.bharati': { en: 'Bharati Base', hi: 'भारती स्टेशन' },
  'topnav.energy': { en: 'Energy Grid', hi: 'ऊर्जा ग्रिड' },
  'topnav.weather': { en: 'Weather & Met', hi: 'मौसम विज्ञान' },
  'topnav.logistics': { en: 'Logistics', hi: 'रसद भंडार' },
  'topnav.alerts': { en: 'Alerts', hi: 'अलर्ट एवं चेतावनी' },
  'topnav.reports': { en: 'Reports', hi: 'दैनिक रिपोर्ट' },
  'topnav.expedition': { en: '45th ISEA', hi: '45वां अंटार्कटिक अभियान' },

  // Breadcrumbs
  'crumb.home': { en: 'Home', hi: 'मुख्य पृष्ठ' },
  'crumb.polar_division': { en: 'Polar Operations Division', hi: 'ध्रुवीय प्रचालन प्रभाग' },
  'crumb.twin': { en: 'Antarctic Stations Real-time Digital Twin', hi: 'अंटार्कटिक स्टेशन रियल-टाइम डिजिटल ट्विन' },

  // Marquee Ticker
  'marquee.label': { en: 'LATEST BULLETINS', hi: 'नवीनतम सूचनाएं' },
  'marquee.notice1': {
    en: '45th Indian Scientific Expedition to Antarctica (ISEA): Telemetry sync active on dual VSAT transponders • Maitri winter crew life-support nominal',
    hi: '45वां भारतीय वैज्ञानिक अंटार्कटिक अभियान (ISEA): दोहरे वीसेट ट्रांसपोंडर पर टेलीमेट्री सिंक सक्रिय • मैत्री विंटर क्रू लाइफ-सपोर्ट सामान्य',
  },
  'marquee.notice2': {
    en: 'Bharati Station satellite uplink signal margin degraded to 12.4 dB due to severe blizzard in Prydz Bay; local edge black-box failover operational',
    hi: 'प्राइड्ज बे में भीषण बर्फीले तूफान के कारण भारती स्टेशन उपग्रह अपलिंक सिग्नल 12.4 dB तक सीमित; स्थानीय एज ब्लैक-बॉक्स स्वायत्त मोड में कार्यरत',
  },

  // Advisory Strip
  'advisory.title': { en: 'OFFICIAL POLAR ADVISORY', hi: 'आधिकारिक ध्रुवीय चेतावनी बुलेटिन' },
  'advisory.all_nominal': { en: 'All polar systems nominal — Station life-support & generators operating within approved parameters', hi: 'सभी प्रणालियां सामान्य — स्टेशन लाइफ-सपोर्ट और जनरेटर स्वीकृत मानकों पर कार्यरत' },
  'advisory.offline': { en: 'Satellite link disconnected — Showing cached telemetry', hi: 'उपग्रह लिंक विच्छेदित — स्थानीय कैश डेटा प्रदर्शित' },
  'advisory.live': { en: 'VSAT TELEMETRY LIVE', hi: 'वीसेट टेलीमेट्री लाइव' },

  // Sidebar
  'nav.wing_title': { en: 'Ministry of Earth Sciences', hi: 'पृथ्वी विज्ञान मंत्रालय' },
  'nav.wing_sub': { en: 'Polar Operations Wing', hi: 'अंटार्कटिक प्रचालन प्रभाग' },
  'nav.dashboard': { en: 'Dashboard', hi: 'मुख्य डैशबोर्ड' },
  'nav.dashboard_sub': { en: 'Live Twin Overview', hi: 'लाइव डिजिटल ट्विन' },
  'nav.stations': { en: 'Station Network', hi: 'स्टेशन नेटवर्क' },
  'nav.stations_sub': { en: 'Maitri & Bharati Nodes', hi: 'मैत्री व भारती नोड्स' },
  'nav.energy': { en: 'Energy Systems', hi: 'ऊर्जा एवं विद्युत' },
  'nav.energy_sub': { en: 'Gensets, Solar, Battery', hi: 'जनरेटर, सौर, बैटरी' },
  'nav.logistics': { en: 'Logistics & Fuel', hi: 'रसद एवं ईंधन भंडार' },
  'nav.logistics_sub': { en: 'Resupply Inventory', hi: 'आपूर्ति प्रबंधन' },
  'nav.environment': { en: 'Environment & Met', hi: 'पर्यावरण एवं मौसम' },
  'nav.environment_sub': { en: 'Sensors & Atmospheric', hi: 'सेंसर व वायुमंडलीय डेटा' },
  'nav.infrastructure': { en: 'Infrastructure Twin', hi: 'संरचनात्मक स्थिति' },
  'nav.infrastructure_sub': { en: 'Structural Integrity', hi: 'भवन व उपकरण ढांचा' },
  'nav.analytics': { en: 'Predictive Analytics', hi: 'पूर्वानुमान विश्लेषण' },
  'nav.analytics_sub': { en: 'AI & Burn Models', hi: 'एआई मॉडल व रुझान' },
  'nav.reports': { en: 'Official Reports', hi: 'सरकारी रिपोर्ट' },
  'nav.reports_sub': { en: 'MoES & GIGW Logs', hi: 'दैनिक व मासिक लॉग' },
  'nav.settings': { en: 'System Settings', hi: 'प्रणाली सेटिंग्स' },
  'nav.settings_sub': { en: 'Link & Security Config', hi: 'सुरक्षा व कॉन्फ़िगरेशन' },
  'nav.switch_to': { en: 'SWITCH TO', hi: 'बदलें:' },
  'nav.digital_india': { en: 'DIGITAL INDIA • MOES POLAR INITIATIVE', hi: 'डिजिटल इंडिया • पृथ्वी विज्ञान मंत्रालय ध्रुवीय पहल' },

  // Station Tabs
  'station.maitri': { en: 'MAITRI BASE', hi: 'मैत्री' },
  'station.maitri_coords': { en: 'East Antarctica (70°45′S)', hi: 'पूर्वी अंटार्कटिका (70°45′द)' },
  'station.bharati': { en: 'BHARATI BASE', hi: 'भारती' },
  'station.bharati_coords': { en: 'Larsemann Hills (69°24′S)', hi: 'लार्समैन हिल्स (69°24′द)' },
  'station.online': { en: 'Online', hi: 'सक्रिय' },
  'station.degraded': { en: 'Weak Signal', hi: 'कमज़ोर सिग्नल' },
  'station.offline': { en: 'Offline', hi: 'ऑफ़लाइन' },
  'station.interval': { en: 'INTERVAL:', hi: 'अवधि:' },
  'station.1h': { en: '1 Hour', hi: '1 घंटा' },
  'station.6h': { en: '6 Hours', hi: '6 घंटे' },
  'station.24h': { en: '24 Hours', hi: '24 घंटे' },

  // Schematic
  'schematic.maitri_title': { en: 'MAITRI BASE — 3D DIGITAL TWIN & SENSORS', hi: 'मैत्री स्टेशन — 3D डिजिटल ट्विन व लाइव सेंसर' },
  'schematic.bharati_title': { en: 'BHARATI BASE — 3D DIGITAL TWIN & SENSORS', hi: 'भारती स्टेशन — 3D डिजिटल ट्विन व लाइव सेंसर' },
  'schematic.confidential': { en: 'OFFICIAL POLAR DIGITAL TWIN • MOES', hi: 'आधिकारिक डिजिटल ट्विन • पृथ्वी विज्ञान मंत्रालय' },
  'schematic.ext_sensors': { en: 'WEATHER SENSORS', hi: 'मौसम संवेदक' },
  'schematic.temp': { en: 'Temp', hi: 'तापमान' },
  'schematic.humidity': { en: 'Humidity', hi: 'आर्द्रता' },
  'schematic.gen_sub': { en: 'POWER STATION', hi: 'मुख्य विद्युत केंद्र' },
  'schematic.status_active': { en: 'Status: Active', hi: 'स्थिति: कार्यरत' },
  'schematic.load': { en: 'Grid Load', hi: 'विद्युत लोड' },

  // Weather Card
  'weather.title': { en: 'WEATHER OBSERVATORY', hi: 'मौसम विज्ञान वेधशाला' },
  'weather.subtitle': { en: 'IMD / NCPOR METEOROLOGY', hi: 'आईएमडी / एनसीपीओआर मेट' },
  'weather.wind': { en: 'Wind', hi: 'पवन' },
  'weather.selected': { en: 'ACTIVE', hi: 'चयनित' },

  // Energy Card
  'energy.title': { en: 'POWER & ENERGY SYSTEMS', hi: 'ऊर्जा एवं विद्युत ग्रिड' },
  'energy.subtitle': { en: 'PRIMARY GRID TELEMETRY', hi: 'मुख्य ग्रिड टेलीमेट्री' },
  'energy.power': { en: 'GEN LOAD', hi: 'जनरेटर भार' },
  'energy.solar': { en: 'SOLAR', hi: 'सौर ऊर्जा' },
  'energy.storage': { en: 'BATTERY', hi: 'बैटरी बैंक' },
  'energy.fuel': { en: 'DIESEL FUEL STOCK', hi: 'डीजल ईंधन भंडार' },

  // Alerts Card
  'alerts.title': { en: 'ACTIVE MISSION ALERTS', hi: 'सक्रिय अलार्म व सुरक्षा चेतावनी' },
  'alerts.total': { en: 'Total', hi: 'कुल' },
  'alerts.loading': { en: 'Loading alerts...', hi: 'अलर्ट लोड हो रहे हैं...' },
  'alerts.none': { en: 'No active alarms (All systems nominal)', hi: 'कोई सक्रिय चेतावनी नहीं (सभी प्रणालियां सामान्य)' },
  'alerts.ack': { en: 'ACK', hi: 'स्वीकार' },

  // Meteorological Mast
  'met.title': { en: 'METEOROLOGICAL MAST', hi: 'मौसम विज्ञान मास्ट (आईएमडी)' },
  'met.wind_speed': { en: 'WIND SPEED', hi: 'पवन गति' },
  'met.direction': { en: 'WIND DIRECTION', hi: 'पवन दिशा' },
  'met.pressure': { en: 'AIR PRESSURE', hi: 'वायुमंडलीय दबाव' },
  'met.solar_rad': { en: 'SOLAR RADIATION', hi: 'सौर विकिरण' },

  // Life Support & Freshwater
  'lss.title': { en: 'WATER & LIFE SUPPORT', hi: 'जल व जीवन रक्षा' },
  'lss.badge': { en: 'ACTIVE', hi: 'सक्रिय' },
  'lss.storage': { en: 'CLEAN WATER IN TANK', hi: 'टैंक में स्वच्छ पानी' },
  'lss.heating': { en: 'PIPE FREEZE GUARD', hi: 'पाइप फ्रीज़ बचाव' },
  'lss.indoor_temp': { en: 'ROOM TEMPERATURE', hi: 'कमरे का तापमान' },
  'lss.air_quality': { en: 'FRESH AIR (OXYGEN)', hi: 'कमरे की ताज़ा हवा' },

  // Glacial & Ice Shelf
  'glacial.title': { en: 'GLACIAL SUB-STRUCTURE & ICE SHELF', hi: 'हिमनद एवं हिम स्तर निगरानी' },
  'glacial.badge': { en: 'ANTARCTIC ICE SHELF RADAR', hi: 'अंटार्कटिक हिम स्तर रडार' },
  'glacial.verified': { en: 'VERIFIED DATA', hi: 'सत्यापित डेटा' },

  // Edge Resilience & Satellite Sync (Disruption-Tolerant Telemetry)
  'edge.title': { en: 'EDGE BLACK-BOX & SATELLITE SYNC', hi: 'एज ब्लैक-बॉक्स एवं उपग्रह सिंक' },
  'edge.badge': { en: 'ISRO / MoES', hi: 'इसरो / एमओईएस' },

  // Seismic & Backup
  'seismic.title': { en: 'EDGE BLACK-BOX & SATELLITE SYNC', hi: 'एज ब्लैक-बॉक्स एवं उपग्रह सिंक' },
  'seismic.live_rec': { en: 'LIVE SYNC', hi: 'लाइव सिंक' },
  'seismic.frequency': { en: 'STORE & FORWARD (DTN)', hi: 'स्टोर एवं फॉरवर्ड (डीटीएन)' },
  'seismic.station_code': { en: 'EDGE NODE', hi: 'एज नोड' },

  // Footer Links & Policies
  'footer.quick_links': { en: 'Government Portal Network', hi: 'सरकारी पोर्टल नेटवर्क' },
  'footer.link_india_gov': { en: 'National Portal of India (india.gov.in)', hi: 'भारत का राष्ट्रीय पोर्टल (india.gov.in)' },
  'footer.link_moes': { en: 'Ministry of Earth Sciences (MoES)', hi: 'पृथ्वी विज्ञान मंत्रालय (MoES)' },
  'footer.link_imd': { en: 'India Meteorological Department (IMD)', hi: 'भारत मौसम विज्ञान विभाग (IMD)' },
  'footer.link_digital_india': { en: 'Digital India Portal', hi: 'डिजिटल इंडिया पोर्टल' },
  'footer.link_mygov': { en: 'MyGov Portal', hi: 'माईगव (MyGov) पोर्टल' },
  'footer.link_rti': { en: 'RTI Online', hi: 'आरटीआई ऑनलाइन' },
  'footer.policies': { en: 'Website Policies', hi: 'वेबसाइट नीतियां' },
  'footer.terms': { en: 'Terms of Use', hi: 'उपयोग की शर्तें' },
  'footer.privacy': { en: 'Privacy Policy', hi: 'गोपनीयता नीति' },
  'footer.copyright_policy': { en: 'Copyright Policy', hi: 'कॉपीराइट नीति' },
  'footer.hyperlink': { en: 'Hyperlinking Policy', hi: 'हाइपरलिंक नीति' },
  'footer.accessibility_stmt': { en: 'Accessibility Statement', hi: 'सुगमता विवरण' },
  'footer.help': { en: 'Help & FAQ', hi: 'सहायता एवं अक्सर पूछे जाने वाले प्रश्न' },
  'footer.feedback': { en: 'Feedback', hi: 'प्रतिक्रिया' },
  'footer.visitors': { en: 'Portal Visitors', hi: 'कुल विज़िटर' },
  'footer.last_updated': { en: 'Last Updated', hi: 'अंतिम नवीनीकरण' },
  'footer.copyright': { en: '© 2026 National Centre for Polar and Ocean Research (NCPOR)', hi: '© 2026 राष्ट्रीय ध्रुवीय एवं समुद्री अनुसंधान केंद्र (एनसीपीओआर)' },
  'footer.ministry': { en: 'Ministry of Earth Sciences, Government of India', hi: 'पृथ्वी विज्ञान मंत्रालय, भारत सरकार' },
  'footer.designed_by': { en: 'Designed, Developed & Maintained for NCPOR, MoES | GIGW 3.0 & NIC Compliant', hi: 'एनसीपीओआर, पृथ्वी विज्ञान मंत्रालय हेतु विकसित एवं संधारित | GIGW 3.0 एवं एनआईसी मानक अनुपालित' },
  'footer.open_alerts': { en: 'Open Alerts', hi: 'सक्रिय अलर्ट' },
  'footer.hq_server': { en: 'HQ Gateway', hi: 'मुख्यालय गेटवे' },
  'footer.connected': { en: 'CONNECTED', hi: 'संलग्न' },
  'footer.satlink': { en: 'VSAT Satellite', hi: 'वीसेट उपग्रह' },
  'footer.stable': { en: 'SECURE', hi: 'सुरक्षित' },

  // Login Page
  'login.heading': { en: 'OFFICER LOGIN PORTAL', hi: 'अधिकारी लॉगिन पोर्टल' },
  'login.subheading': { en: 'National Centre for Polar and Ocean Research (NCPOR), Goa', hi: 'राष्ट्रीय ध्रुवीय एवं समुद्री अनुसंधान केंद्र (एनसीपीओआर), गोवा' },
  'login.portal_title': { en: 'Himantar: Antarctic Digital Twin Command System', hi: 'हिमांतर: अंटार्कटिक डिजिटल ट्विन कमान प्रणाली' },
  'login.restricted_notice': { en: 'CONFIDENTIAL • GOVT. OF INDIA SYSTEM', hi: 'गोपनीय • भारत सरकार प्रणाली' },
  'login.statutory_warning': {
    en: 'STATUTORY WARNING: Unauthorized access is strictly prohibited under the Information Technology Act, 2000 (Section 43 & 66). All network activities are actively logged, audited, and monitored by CERT-In and NIC security gateways.',
    hi: 'वैधानिक चेतावनी: सूचना प्रौद्योगिकी अधिनियम, 2000 (धारा 43 एवं 66) के अंतर्गत इस सुरक्षित प्रणाली पर अनधिकृत पहुंच दंडनीय अपराध है। सभी नेटवर्क गतिविधियों की निगरानी सीईआरटी-इन (CERT-In) और एनआईसी सुरक्षा गेटवे द्वारा की जाती है।',
  },
  'login.username': { en: 'OFFICER ID / GOVT EMAIL', hi: 'अधिकारी पहचान / सरकारी ईमेल' },
  'login.password': { en: 'PASSWORD', hi: 'पासवर्ड' },
  'login.captcha': { en: 'ENTER SECURITY CAPTCHA', hi: 'सुरक्षा कैप्चा दर्ज करें' },
  'login.button': { en: 'SECURE AUTHENTICATE', hi: 'सुरक्षित लॉगिन' },
  'login.authenticating': { en: 'AUTHENTICATING WITH NIC HQ...', hi: 'प्रमाणीकरण जारी है...' },
  'login.dev_helper': { en: 'Test Credentials (Pre-configured):', hi: 'परीक्षण क्रेडेंशियल (पूर्व-कॉन्फ़िगर):' },
}

interface LanguageContextType {
  lang: Language
  setLang: (lang: Language) => void
  toggleLang: () => void
  t: (key: string) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    const saved = localStorage.getItem('himantar_lang') || localStorage.getItem('vajrax_lang')
    return (saved === 'hi' || saved === 'en') ? saved : 'hi'
  })

  useEffect(() => {
    localStorage.setItem('himantar_lang', lang)
    document.documentElement.lang = lang
  }, [lang])

  function setLang(newLang: Language) {
    setLangState(newLang)
  }

  function toggleLang() {
    setLangState(prev => (prev === 'hi' ? 'en' : 'hi'))
  }

  function t(key: string): string {
    const entry = DICTIONARY[key]
    if (!entry) return key
    return entry[lang] ?? entry['en'] ?? key
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useLanguage must be used within LanguageProvider')
  }
  return ctx
}
