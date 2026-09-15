import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { SocketProvider } from './context/SocketContext'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardLayout from './components/DashboardLayout'
import LandingPage from './pages/LandingPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import PostEventReportPage from './pages/PostEventReportPage.jsx'

import DashboardPage from './pages/coordinator/DashboardPage.jsx'
import RoutePlanPage from './pages/coordinator/RoutePlanPage.jsx'
import SimulationPage from './pages/coordinator/SimulationPage.jsx'
import ZonalAnalysisPage from './pages/coordinator/ZonalAnalysisPage.jsx'
import ShelterStatusPage from './pages/coordinator/ShelterStatusPage.jsx'

import RoutePlanningPage from './pages/zone_admin/RoutePlanningPage.jsx'
import ShelterManagementPage from './pages/zone_admin/ShelterManagementPage.jsx'
import ZoneStatusPage from './pages/zone_admin/ZoneStatusPage.jsx'

import EmergencySOSPage from './pages/citizen/EmergencySOSPage.jsx'
import ReportFilingPage from './pages/citizen/ReportFilingPage.jsx'
import DirectionsPage from './pages/citizen/DirectionsPage.jsx'

import NDRFPage from './pages/ndrf/NDRFPage.jsx'

function withLayout(roles, Page) {
  return (
    <ProtectedRoute roles={roles}>
      <DashboardLayout>
        <Page />
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SocketProvider>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />

            <Route path="/dashboard" element={withLayout(['central_coordinator'], DashboardPage)} />
            <Route path="/dashboard/route-plan" element={withLayout(['central_coordinator'], RoutePlanPage)} />
            <Route path="/dashboard/simulation" element={withLayout(['central_coordinator'], SimulationPage)} />
            <Route path="/dashboard/zonal-analysis" element={withLayout(['central_coordinator'], ZonalAnalysisPage)} />
            <Route path="/dashboard/shelter-status" element={withLayout(['central_coordinator'], ShelterStatusPage)} />

            <Route path="/dashboard/zone" element={withLayout(['zone_admin'], RoutePlanningPage)} />
            <Route path="/dashboard/zone/shelter-management" element={withLayout(['zone_admin'], ShelterManagementPage)} />
            <Route path="/dashboard/zone/status" element={withLayout(['zone_admin'], ZoneStatusPage)} />

            <Route path="/dashboard/citizen" element={withLayout(['citizen'], EmergencySOSPage)} />
            <Route path="/dashboard/citizen/report" element={withLayout(['citizen'], ReportFilingPage)} />
            <Route path="/dashboard/citizen/directions" element={withLayout(['citizen'], DirectionsPage)} />

            <Route path="/dashboard/rescue" element={withLayout(['ndrf'], NDRFPage)} />

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
