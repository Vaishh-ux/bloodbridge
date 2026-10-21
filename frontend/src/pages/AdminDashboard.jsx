import { useCallback, useEffect, useState } from 'react'
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip } from 'chart.js'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import { Activity, Building2, CheckCircle2, Flag, ShieldAlert, Siren, Users } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, timeAgo } from '../lib/blood'
import { useToast } from '../context/ToastContext'
import { ErrorBox, PageHeader, Spinner, StatCard, StatusBadge, UrgencyBadge } from '../components/ui'

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend)
const PALETTE = ['#e11d48', '#be123c', '#f97316', '#f59e0b', '#0ea5e9', '#2563eb', '#10b981', '#64748b']

function ChartCard({ title, children, empty }) {
  return (
    <div className="card p-5 min-w-0">
      <p className="font-black text-navy-900 text-sm mb-3">{title}</p>
      {empty ? <p className="text-sm text-slate-400 py-10 text-center">No chart data</p> : <div className="h-56 relative">{children}</div>}
    </div>
  )
}
const opts = { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }

export default function AdminDashboard() {
  const toast = useToast()
  const [tab, setTab] = useState('users')
  const [stats, setStats] = useState(null)
  const [an, setAn] = useState(null)
  const [users, setUsers] = useState([])
  const [reqs, setReqs] = useState([])
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState({ role: '', search: '' })
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try {
      const params = Object.fromEntries(Object.entries(filter).filter(([, v]) => v))
      const [a, b, c, d, e] = await Promise.all([api.get('/admin/dashboard'), api.get('/admin/analytics'), api.get('/admin/users', { params }), api.get('/admin/requests'), api.get('/admin/audit-logs', { params: { limit: 50 } })])
      setStats(a.data); setAn(b.data); setUsers(c.data); setReqs(d.data); setLogs(e.data); setErr('')
    } catch (e2) { setErr(errorMessage(e2)) }
  }, [filter])
  useEffect(() => { load() }, [load])

  const act = async (fn) => { try { const r = await fn(); toast.success(r.data.message); load() } catch (e) { toast.error(errorMessage(e)) } }
  if (!stats && !err) return <Spinner />

  const bg = an?.blood_group_distribution || {}
  const em = an?.emergency_breakdown || {}
  const city = an?.requests_per_city || {}
  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <PageHeader icon={ShieldAlert} title="System Administration" subtitle="Blood Bridge platform metrics, verification & security audit" />
      <ErrorBox message={err} onRetry={load} />
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard icon={Users} label="Total users" value={stats.total_users} />
          <StatCard icon={Users} label="Donors" value={stats.total_donors} tone="text-sky-500" />
          <StatCard icon={Building2} label="Hospitals" value={stats.total_hospitals} hint={`${stats.unverified_hospitals} unverified`} tone="text-slate-500" />
          <StatCard icon={Activity} label="Active requests" value={stats.active_requests} tone="text-amber-500" />
          <StatCard icon={CheckCircle2} label="Completed donations" value={stats.completed_donations} tone="text-emerald-500" />
          <StatCard icon={Siren} label="Critical (active)" value={stats.emergency_requests} tone="text-red-600" />
        </div>
      )}
      {an && (
        <div className="grid md:grid-cols-2 gap-4">
          <ChartCard title="Donor Blood Group Distribution" empty={!Object.keys(bg).length}>
            <Doughnut data={{ labels: BLOOD_GROUPS.filter((g) => bg[g]), datasets: [{ data: BLOOD_GROUPS.filter((g) => bg[g]).map((g) => bg[g]), backgroundColor: PALETTE }] }}
                      options={{ maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }} />
          </ChartCard>
          <ChartCard title="Requests Over Time (30 days)">
            <Line data={{ labels: an.requests_over_time.map((d) => d.date.slice(5)), datasets: [{ data: an.requests_over_time.map((d) => d.count), borderColor: '#e11d48', backgroundColor: '#e11d4822', fill: true, tension: 0.3 }] }} options={opts} />
          </ChartCard>
          <ChartCard title="Requests by Emergency Severity" empty={!Object.keys(em).length}>
            <Bar data={{ labels: ['Critical', 'High', 'Medium', 'Normal'], datasets: [{ data: ['Critical', 'High', 'Medium', 'Normal'].map((k) => em[k] || 0), backgroundColor: ['#dc2626', '#ea580c', '#d97706', '#64748b'] }] }} options={opts} />
          </ChartCard>
          <ChartCard title="Requests by City" empty={!Object.keys(city).length}>
            <Bar data={{ labels: Object.keys(city), datasets: [{ data: Object.values(city), backgroundColor: '#0f172a' }] }} options={{ ...opts, indexAxis: 'y', scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } }} />
          </ChartCard>
        </div>
      )}
      {an?.average_minutes_to_first_acceptance != null && <p className="text-sm text-slate-600">Average time to first donor acceptance: <strong>{an.average_minutes_to_first_acceptance} min</strong></p>}

      <div className="card p-6">
        <div className="flex flex-wrap gap-2 mb-4" role="tablist">
          {[['users', 'Users'], ['requests', 'Requests'], ['audit', 'Audit log']].map(([k, l]) => (
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`btn-sm btn ${tab === k ? 'bg-navy-900 text-white' : 'bg-slate-100 text-slate-600'}`}>{l}</button>
          ))}
        </div>
        {tab === 'users' && (
          <>
            <form className="flex flex-wrap gap-2 mb-4" onSubmit={(e) => { e.preventDefault(); load() }}>
              <select className="input py-2 w-auto" value={filter.role} onChange={(e) => setFilter({ ...filter, role: e.target.value })} aria-label="Role">
                <option value="">All Roles</option><option value="DONOR">Donor</option><option value="PATIENT">Patient</option><option value="HOSPITAL">Hospital</option><option value="ADMIN">Admin</option>
              </select>
              <input className="input py-2 w-56" placeholder="Search name or email" value={filter.search} onChange={(e) => setFilter({ ...filter, search: e.target.value })} />
              <button className="btn-primary btn-sm">Filter</button>
            </form>
            <div className="overflow-x-auto"><table className="w-full text-sm min-w-[760px]">
              <thead className="text-xs uppercase text-slate-500 bg-slate-50"><tr><th className="text-left p-3">ID</th><th className="text-left p-3">Name</th><th className="text-left p-3">Email</th><th className="text-left p-3">Role</th><th className="text-left p-3">Verified</th><th className="text-left p-3">Status</th><th className="text-left p-3">Actions</th></tr></thead>
              <tbody>{users.map((u) => (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="p-3">{u.id}</td><td className="p-3 font-bold">{u.name}</td><td className="p-3 text-slate-500">{u.email}</td><td className="p-3">{u.role}</td>
                  <td className="p-3">{u.is_verified ? <span className="chip bg-emerald-50 text-emerald-700">Verified</span> : <span className="chip bg-slate-100 text-slate-500">No</span>}</td>
                  <td className="p-3">{u.is_blocked ? <span className="chip bg-red-50 text-red-700">Blocked</span> : <span className="chip bg-emerald-50 text-emerald-700">Active</span>}</td>
                  <td className="p-3 space-x-3 whitespace-nowrap">
                    <button className="text-xs font-bold text-sky-700" onClick={() => act(() => api.put(`/admin/users/${u.id}/verify`, null, { params: { verified: !u.is_verified } }))}>{u.is_verified ? 'Unverify' : 'Verify Now'}</button>
                    {u.role !== 'ADMIN' && <button className="text-xs font-bold text-red-600" onClick={() => window.confirm(`${u.is_blocked ? 'Unblock' : 'Block'} ${u.name}?`) && act(() => api.put(`/admin/users/${u.id}/block`, null, { params: { blocked: !u.is_blocked } }))}>{u.is_blocked ? 'Unblock' : 'Block'}</button>}
                  </td>
                </tr>
              ))}</tbody>
            </table></div>
          </>
        )}
        {tab === 'requests' && (
          <div className="overflow-x-auto"><table className="w-full text-sm min-w-[760px]">
            <thead className="text-xs uppercase text-slate-500 bg-slate-50"><tr><th className="text-left p-3">ID</th><th className="text-left p-3">Blood</th><th className="text-left p-3">Hospital</th><th className="text-left p-3">City</th><th className="text-left p-3">Emergency</th><th className="text-left p-3">Status</th><th className="text-left p-3">Created</th><th className="text-left p-3">Review</th></tr></thead>
            <tbody>{reqs.map((r) => (
              <tr key={r.id} className={`border-t border-slate-100 ${r.is_suspicious ? 'bg-red-50/50' : ''}`}>
                <td className="p-3">#{r.id}</td><td className="p-3 font-black text-blood-600">{r.blood_group} ×{r.units_required}</td><td className="p-3">{r.hospital_name}</td><td className="p-3">{r.city}</td>
                <td className="p-3"><UrgencyBadge level={r.emergency_level} /></td><td className="p-3"><StatusBadge status={r.status} /></td><td className="p-3 text-slate-500">{timeAgo(r.created_at)}</td>
                <td className="p-3"><button className="text-xs font-bold text-red-600 flex items-center gap-1" onClick={() => act(() => api.put(`/admin/requests/${r.id}/flag-suspicious`, null, { params: { is_suspicious: !r.is_suspicious } }))}>
                  <Flag className="w-3 h-3" />{r.is_suspicious ? 'Unflag' : 'Flag suspicious'}</button></td>
              </tr>
            ))}</tbody>
          </table>
          <p className="text-xs text-slate-500 mt-2">Flagged requests are hidden from the public feed and map.</p></div>
        )}
        {tab === 'audit' && (
          <div className="overflow-x-auto"><table className="w-full text-sm min-w-[640px]">
            <thead className="text-xs uppercase text-slate-500 bg-slate-50"><tr><th className="text-left p-3">When</th><th className="text-left p-3">User</th><th className="text-left p-3">Action</th><th className="text-left p-3">Entity</th><th className="text-left p-3">Details</th></tr></thead>
            <tbody>{logs.map((l) => (
              <tr key={l.id} className="border-t border-slate-100"><td className="p-3 text-slate-500">{timeAgo(l.created_at)}</td><td className="p-3">{l.user_id ?? '—'}</td><td className="p-3 font-bold">{l.action}</td><td className="p-3">{l.entity} {l.entity_id}</td><td className="p-3 text-slate-500">{l.details}</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  )
}
