import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth } from './context/AuthContext'
import { DASHBOARD_PATH } from './lib/blood'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Requests from './pages/Requests'
import CreateRequest from './pages/CreateRequest'
import FindDonors from './pages/FindDonors'
import BloodBanks from './pages/BloodBanks'
import EmergencyMapPage from './pages/EmergencyMapPage'
import EmergencyHelp from './pages/EmergencyHelp'
import DonateBlood from './pages/DonateBlood'
import DonorDashboard from './pages/DonorDashboard'
import PatientDashboard from './pages/PatientDashboard'
import HospitalDashboard from './pages/HospitalDashboard'
import AdminDashboard from './pages/AdminDashboard'
import Notifications from './pages/Notifications'
import NotFound from './pages/NotFound'
import { Spinner } from './components/ui'

function DashboardRedirect() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return <Navigate to={user ? DASHBOARD_PATH[user.role] : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/requests" element={<Requests />} />
        <Route path="/find-donors" element={<FindDonors />} />
        <Route path="/blood-banks" element={<BloodBanks />} />
        <Route path="/map" element={<EmergencyMapPage />} />
        <Route path="/emergency" element={<EmergencyHelp />} />
        <Route path="/donate" element={<DonateBlood />} />
        <Route path="/dashboard" element={<DashboardRedirect />} />
        <Route path="/create-request" element={<CreateRequest />} />
        <Route path="/donor-dashboard" element={<ProtectedRoute roles={['DONOR']}><DonorDashboard /></ProtectedRoute>} />
        <Route path="/patient-dashboard" element={<ProtectedRoute roles={['PATIENT']}><PatientDashboard /></ProtectedRoute>} />
        <Route path="/hospital-dashboard" element={<ProtectedRoute roles={['HOSPITAL']}><HospitalDashboard /></ProtectedRoute>} />
        <Route path="/admin-dashboard" element={<ProtectedRoute roles={['ADMIN']}><AdminDashboard /></ProtectedRoute>} />
        <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
