import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardList, Phone, RefreshCcw, Users } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useRealtimeEvent } from '../context/RealtimeContext'
import StatusTracker from '../components/StatusTracker'
import { BloodBadge, Empty, ErrorBox, Modal, PageHeader, Skeleton, Spinner, StatusBadge, UrgencyBadge } from '../components/ui'

export function MatchesModal({ requestId, onClose }) {
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')
  const load = useCallback(() => {
    api.get(`/matching/${requestId}`).then((r) => setRows(r.data)).catch((e) => setErr(errorMessage(e)))
  }, [requestId])
  useEffect(() => { if (requestId) load() }, [requestId, load])
  useRealtimeEvent(() => requestId && load(), ['NOTIFICATION_NEW', 'REQUEST_UPDATED'])
  return (
    <Modal open={!!requestId} title={`Matched donors · request #${requestId}`} onClose={onClose}>
      <ErrorBox message={err} />
      {rows === null && !err ? <Spinner /> : rows?.length === 0 ? <p className="text-sm text-slate-500">No matches found for this request yet. New compatible donors are matched automatically.</p> : (
        <ul className="divide-y divide-slate-100">
          {rows?.map((m) => (
            <li key={m.match_id} className="py-3 flex items-center gap-3">
              <BloodBadge group={m.donor_blood_group} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="font-bold text-slate-800">{m.donor_name}</p>
                <p className="text-xs text-slate-500">{m.city}{m.distance_km != null ? ` · ${m.distance_km} km` : ''} · score {m.match_score}%</p>
              </div>
              <div className="text-right">
                <span className={`chip ${m.match_status === 'ACCEPTED' || m.match_status === 'CONFIRMED' ? 'bg-emerald-50 text-emerald-700' : m.match_status === 'PENDING' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-500'}`}>{m.match_status}</span>
                {m.donor_phone && <a href={`tel:${m.donor_phone}`} className="flex items-center gap-1 text-sm font-bold text-blood-600 mt-1"><Phone className="w-4 h-4" />{m.donor_phone}</a>}
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-slate-500 mt-4">Contact numbers appear only after a donor accepts. Please coordinate through the hospital blood bank.</p>
    </Modal>
  )
}

export default function PatientDashboard() {
  const { user } = useAuth()
  const toast = useToast()
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')
  const [view, setView] = useState(null)
  const [busy, setBusy] = useState(null)

  const load = useCallback(async () => {
    try { const { data } = await api.get('/requests/mine'); setRows(data); setErr('') } catch (e) { setErr(errorMessage(e)) }
  }, [])
  useEffect(() => { load() }, [load])
  useRealtimeEvent(load, ['NOTIFICATION_NEW', 'REQUEST_UPDATED'])

  const act = async (key, fn, confirmText) => {
    if (confirmText && !window.confirm(confirmText)) return
    setBusy(key)
    try { const r = await fn(); toast.success(r.data.message || 'Done.'); load() } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(null) }
  }

  const active = rows?.filter((r) => !['COMPLETED', 'CANCELLED'].includes(r.status)) || []
  const past = rows?.filter((r) => ['COMPLETED', 'CANCELLED'].includes(r.status)) || []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <PageHeader icon={ClipboardList} title="Patient Blood Request Center" subtitle={`Welcome, ${user.name} · monitor real-time matching status for your requests`}>
        <Link to="/create-request" className="btn-primary">+ Create Blood Request</Link>
      </PageHeader>
      <ErrorBox message={err} onRetry={load} />
      {rows === null ? <Skeleton /> : active.length === 0 ? (
        <Empty title="No Active Blood Requests">Click “Create Blood Request” to alert compatible donors near the hospital.</Empty>
      ) : (
        <div className="space-y-5">
          {active.map((r) => (
            <article key={r.id} className="card p-6">
              <div className="flex flex-wrap gap-4 items-start">
                <BloodBadge group={r.blood_group} size="lg" />
                <div className="flex-1 min-w-[200px]">
                  <div className="flex flex-wrap gap-2 items-center"><UrgencyBadge level={r.emergency_level} /><StatusBadge status={r.status} /><span className="text-xs text-slate-400">#{r.id}</span></div>
                  <p className="font-black text-navy-900 mt-2">{r.units_required} unit(s) at {r.hospital_name}</p>
                  <p className="text-sm text-slate-500">{r.hospital_address}, {r.city} · needed {r.required_date} {r.required_time}</p>
                  <p className="text-sm text-slate-600 mt-1">
                    <strong>{r.matches_total}</strong> donor(s) matched · <strong className="text-emerald-600">{r.matches_accepted}</strong> accepted · {r.units_fulfilled}/{r.units_required} unit(s) confirmed
                  </p>
                </div>
              </div>
              <div className="mt-5"><StatusTracker status={r.status} /></div>
              {r.status === 'SEARCHING' && <p className="mt-4 text-sm text-amber-700 bg-amber-50 rounded-xl p-3">No compatible available donor in range yet — we keep matching new donors automatically. Please also contact the hospital blood bank directly.</p>}
              <div className="flex flex-wrap gap-2 mt-5">
                <button className="btn-dark btn-sm" onClick={() => setView(r.id)}><Users className="w-4 h-4" /> View Matched Donors</button>
                <button className="btn-ghost btn-sm" disabled={busy === `m${r.id}`} onClick={() => act(`m${r.id}`, () => api.post(`/matching/${r.id}`))}><RefreshCcw className="w-4 h-4" /> Search again</button>
                <button className="btn-ghost btn-sm" disabled={busy === `f${r.id}`} onClick={() => act(`f${r.id}`, () => api.post(`/requests/${r.id}/fulfilled`), 'Mark this request as fulfilled? Donors will stop being alerted.')}>Mark fulfilled</button>
                <button className="btn-sm btn text-red-600 hover:bg-red-50" disabled={busy === `c${r.id}`} onClick={() => act(`c${r.id}`, () => api.post(`/requests/${r.id}/cancel`), 'Cancel this request? Matched donors will be told it is no longer needed.')}>Cancel Request</button>
              </div>
            </article>
          ))}
        </div>
      )}

      {past.length > 0 && (
        <section className="mt-10">
          <h2 className="text-lg font-black text-navy-900 mb-3">Request History</h2>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm min-w-[560px]">
              <thead className="text-xs uppercase text-slate-500 bg-slate-50"><tr><th className="text-left p-3">ID</th><th className="text-left p-3">Blood</th><th className="text-left p-3">Hospital</th><th className="text-left p-3">Units</th><th className="text-left p-3">Status</th><th className="p-3" /></tr></thead>
              <tbody>{past.map((r) => (
                <tr key={r.id} className="border-t border-slate-100"><td className="p-3">#{r.id}</td><td className="p-3 font-bold text-blood-600">{r.blood_group}</td><td className="p-3">{r.hospital_name}</td><td className="p-3">{r.units_fulfilled}/{r.units_required}</td><td className="p-3"><StatusBadge status={r.status} /></td>
                  <td className="p-3 text-right"><button className="text-xs font-bold text-blood-600" onClick={() => setView(r.id)}>Donors</button></td></tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}
      <MatchesModal requestId={view} onClose={() => setView(null)} />
    </div>
  )
}
