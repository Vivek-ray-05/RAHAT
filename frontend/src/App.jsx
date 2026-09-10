import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { SocketProvider } from './context/SocketContext'
import ProtectedRoute from './components/ProtectedRoute'
import LandingPage from './pages/LandingPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import CoordinatorDashboard from './pages/CoordinatorDashboard.jsx'
import CitizenDashboard from './pages/CitizenDashboard.jsx'
import ZoneAdminDashboard from './pages/ZoneAdminDashboard.jsx'
import NDRFDashboard from './pages/NDRFDashboard.jsx'
import PostEventReportPage from './pages/PostEventReportPage.jsx'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SocketProvider>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute roles={['central_coordinator']}>
                  <CoordinatorDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/citizen"
              element={
                <ProtectedRoute roles={['citizen']}>
                  <CitizenDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/zone"
              element={
                <ProtectedRoute roles={['zone_admin']}>
                  <ZoneAdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/rescue"
              element={
                <ProtectedRoute roles={['ndrf']}>
                  <NDRFDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/report/:runId"
              element={
                <ProtectedRoute roles={['central_coordinator', 'zone_admin', 'ndrf']}>
                  <PostEventReportPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </SocketProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
