import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { DASHBOARD_PATH } from '../lib/blood'
import { Spinner } from './ui'

export default function ProtectedRoute({ roles, children }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16">
        <div className="card p-8 text-center">
          <p className="font-black text-xl text-navy-900">Not available for your account</p>
          <p className="text-sm text-slate-500 mt-2">This page is for {roles.map((r) => r.toLowerCase()).join(' / ')} accounts.</p>
          <a href={DASHBOARD_PATH[user.role]} className="btn-primary mt-6">Go to my dashboard</a>
        </div>
      </div>
    )
  }
  return children
}
