import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { LanguageProvider } from './context/LanguageContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import StationsPage from './pages/StationsPage'
import EnergyPage from './pages/EnergyPage'
import LogisticsPage from './pages/LogisticsPage'
import EnvironmentPage from './pages/EnvironmentPage'
import InfrastructurePage from './pages/InfrastructurePage'
import AnalyticsPage from './pages/AnalyticsPage'
import ReportsPage from './pages/ReportsPage'
import SettingsPage from './pages/SettingsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/stations" element={<ProtectedRoute><StationsPage /></ProtectedRoute>} />
          <Route path="/energy" element={<ProtectedRoute><EnergyPage /></ProtectedRoute>} />
          <Route path="/logistics" element={<ProtectedRoute><LogisticsPage /></ProtectedRoute>} />
          <Route path="/environment" element={<ProtectedRoute><EnvironmentPage /></ProtectedRoute>} />
          <Route path="/infrastructure" element={<ProtectedRoute><InfrastructurePage /></ProtectedRoute>} />
          <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/*" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        </Routes>
      </AuthProvider>
    </LanguageProvider>
  )
}
