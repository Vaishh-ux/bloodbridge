import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, HeartHandshake, Map as MapIcon } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, URGENCY, canDonateTo } from '../lib/blood'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useRealtimeEvent } from '../context/RealtimeContext'
import RequestCard from '../components/RequestCard'
import { Empty, ErrorBox, PageHeader, Skeleton } from '../components/ui'

export default function Requests() {
  const { user } = useAuth()
  const toast = useToast()
  const [filters, setFilters] = useState({ blood_group: '', emergency_level: '', city: '' })
  const [applied, setApplied] = useState(filters)
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setErr('')
    try {
      const params = Object.fromEntries(Object.entries(applied).filter(([, v]) => v))
      const { data } = await api.get('/requests', { params })
      setRows(data)
    } catch (e) { setErr(errorMessage(e)); setRows([]) }
  }, [applied])
  useEffect(() => { load() }, [load])
  useRealtimeEvent(load, ['REQUEST_NEW', 'REQUEST_UPDATED'])

  const donorGroup = user?.role === 'DONOR' ? user.profile?.blood_group : null
  const respond = async (r) => {
    setBusyId(r.id)
    try {
      const { data } = await api.post(`/requests/${r.id}/respond`)
      toast.success(data.message, 'Response sent')
      load()
    } catch (e) { toast.error(errorMessage(e), 'Could not respond') } finally { setBusyId(null) }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <PageHeader icon={Activity} title={`Live Emergency Blood Requests (${rows?.length ?? 0})`}
                  subtitle="Real-time broadcasted blood requests seeking compatible donors · most urgent first">
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); setApplied(filters) }}>
          <select className="input py-2 w-auto font-bold text-blood-600" value={filters.blood_group} onChange={(e) => setFilters({ ...filters, blood_group: e.target.value })} aria-label="Blood group">
            <option value="">All Blood Groups</option>{BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
          </select>
          <select className="input py-2 w-auto font-bold" value={filters.emergency_level} onChange={(e) => setFilters({ ...filters, emergency_level: e.target.value })} aria-label="Severity">
            <option value="">All Severities</option>{URGENCY.map((u) => <option key={u}>{u}</option>)}
          </select>
          <input className="input py-2 w-40" placeholder="Search by city…" value={filters.city} onChange={(e) => setFilters({ ...filters, city: e.target.value })} aria-label="City" />
          <button className="btn-primary btn-sm">Search</button>
          <Link to="/map" className="btn-ghost btn-sm"><MapIcon className="w-4 h-4" /> Map</Link>
        </form>
      </PageHeader>

      {!user && (
        <div className="mb-6 rounded-2xl bg-blood-50 border border-blood-100 p-4 text-sm text-blood-800">
          Want to help? <Link to="/register?role=DONOR" className="font-bold underline">Register as a donor</Link> to respond to requests and get alerts for matches near you.
        </div>
      )}
      {donorGroup && (
        <div className="mb-6 rounded-2xl bg-sky-50 border border-sky-100 p-4 text-sm text-sky-800">
          Your blood group <strong>{donorGroup}</strong> can be given to: <strong>{canDonateTo(donorGroup).join(', ')}</strong>. Compatible requests show an “I can donate” button.
        </div>
      )}
      <ErrorBox message={err} onRetry={load} />
      {rows === null ? <Skeleton rows={4} /> : rows.length === 0 ? (
        <Empty title="No blood requests matching filters.">Active requests appear here the moment they are created.</Empty>
      ) : (
        <div className="space-y-4 mt-2">
          {rows.map((r) => (
            <RequestCard key={r.id} req={r}>
              {donorGroup && canDonateTo(donorGroup).includes(r.blood_group) && !['COMPLETED', 'CANCELLED'].includes(r.status) && (
                <button className="btn-primary btn-sm" disabled={busyId === r.id} onClick={() => respond(r)}>
                  <HeartHandshake className="w-4 h-4" /> I can donate
                </button>
              )}
              {!user && <Link to="/login" className="btn-ghost btn-sm">Log in to respond</Link>}
            </RequestCard>
          ))}
        </div>
      )}
    </div>
  )
}
