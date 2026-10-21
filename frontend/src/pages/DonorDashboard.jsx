import { useCallback, useEffect, useState } from 'react'
import { Activity, Award, Check, HeartHandshake, HeartPulse, MapPin, Navigation, Phone, Settings, ShieldCheck, X } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, URGENCY, todayISO } from '../lib/blood'
import { directionsUrl } from '../lib/geo'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useRealtimeEvent } from '../context/RealtimeContext'
import RequestCard from '../components/RequestCard'
import { LocationPicker } from '../components/MapView'
import { BloodBadge, Empty, ErrorBox, Field, Modal, Skeleton, Spinner, StatCard } from '../components/ui'

function ProfileEditor({ me, onSaved, onClose }) {
  const toast = useToast()
  const [f, setF] = useState({
    phone: me.phone || '', blood_group: me.blood_group, city: me.city, state: me.state, pincode: me.pincode || '',
    address: me.address || '', last_donation_date: me.last_donation_date || '', date_of_birth: me.date_of_birth || '',
    meets_basic_criteria: me.screening_passed, loc: me.latitude != null ? { lat: me.latitude, lng: me.longitude } : null,
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e?.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e }))
  const save = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      await api.put('/donors/profile', {
        phone: f.phone || null, blood_group: f.blood_group, city: f.city, state: f.state, pincode: f.pincode || null,
        address: f.address || null, last_donation_date: f.last_donation_date || null, date_of_birth: f.date_of_birth || null,
        meets_basic_criteria: f.meets_basic_criteria, latitude: f.loc?.lat ?? null, longitude: f.loc?.lng ?? null,
      })
      toast.success('Profile updated.'); onSaved(); onClose()
    } catch (e2) { setErr(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={save} className="space-y-4">
      <div className="grid sm:grid-cols-3 gap-4">
        <Field label="Blood group"><select className="input" value={f.blood_group} onChange={set('blood_group')}>{BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}</select></Field>
        <Field label="Date of birth"><input type="date" className="input" max={todayISO()} value={f.date_of_birth} onChange={set('date_of_birth')} /></Field>
        <Field label="Last donation"><input type="date" className="input" max={todayISO()} value={f.last_donation_date} onChange={set('last_donation_date')} /></Field>
        <Field label="Phone"><input className="input" value={f.phone} onChange={set('phone')} /></Field>
        <Field label="City"><input className="input" value={f.city} onChange={set('city')} /></Field>
        <Field label="State"><input className="input" value={f.state} onChange={set('state')} /></Field>
        <Field label="PIN code"><input className="input" value={f.pincode} onChange={set('pincode')} /></Field>
        <div className="sm:col-span-2"><Field label="Address / area"><input className="input" value={f.address} onChange={set('address')} /></Field></div>
      </div>
      <LocationPicker value={f.loc} onChange={set('loc')} label="Approximate location" addressHint={[f.address, f.city, f.pincode].filter(Boolean).join(', ')} />
      <label className="flex gap-3 text-sm text-slate-700">
        <input type="checkbox" className="accent-blood-600 mt-0.5" checked={f.meets_basic_criteria} onChange={set('meets_basic_criteria')} />
        I meet the basic screening questions (18–65 years, ≥45 kg, healthy today, no known deferral).
      </label>
      <ErrorBox message={err} />
      <button className="btn-primary w-full" disabled={busy}>Save profile</button>
    </form>
  )
}

export default function DonorDashboard() {
  const { user, refresh } = useAuth()
  const toast = useToast()
  const [me, setMe] = useState(null)
  const [matches, setMatches] = useState(null)
  const [nearby, setNearby] = useState(null)
  const [donations, setDonations] = useState([])
  const [filters, setFilters] = useState({ max_distance_km: 50, emergency_level: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(null)
  const [editing, setEditing] = useState(false)

  const load = useCallback(async () => {
    try {
      const params = { max_distance_km: filters.max_distance_km }
      if (filters.emergency_level) params.emergency_level = filters.emergency_level
      const [a, b, c, d] = await Promise.all([
        api.get('/donors/me'), api.get('/donors/matches'), api.get('/donors/requests/nearby', { params }), api.get('/donors/donations'),
      ])
      setMe(a.data); setMatches(b.data); setNearby(c.data); setDonations(d.data); setErr('')
    } catch (e) { setErr(errorMessage(e)) }
  }, [filters])
  useEffect(() => { load() }, [load])
  useRealtimeEvent(load, ['NOTIFICATION_NEW', 'REQUEST_NEW', 'REQUEST_UPDATED'])

  const act = async (key, fn, okMsg) => {
    setBusy(key)
    try { const r = await fn(); toast.success(r?.data?.message || okMsg); await load(); refresh() }
    catch (e) { toast.error(errorMessage(e)) } finally { setBusy(null) }
  }
  const toggle = () => act('avail', () => api.put('/donors/availability', { available: !me.available }),
    me.available ? 'You are now unavailable.' : 'You are now available for emergency requests.')

  if (!me && !err) return <Spinner />
  const pending = matches?.filter((m) => m.match_status === 'PENDING' && !['COMPLETED', 'CANCELLED'].includes(m.request_status)) || []
  const active = matches?.filter((m) => m.match_status === 'ACCEPTED') || []
  const history = matches?.filter((m) => !pending.includes(m) && !active.includes(m)) || []

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <ErrorBox message={err} onRetry={load} />
      {me && (
        <>
          <div className="card p-6 flex flex-col md:flex-row md:items-center gap-5">
            <BloodBadge group={me.blood_group} size="lg" />
            <div className="flex-1">
              <h1 className="text-2xl font-black text-navy-900">Welcome, {user.name}</h1>
              <p className="text-sm text-slate-500">Donor · {me.city}, {me.state} · can donate to {me.can_donate_to.join(', ')}</p>
              <p className={`text-sm mt-1 font-bold ${me.eligible ? 'text-emerald-600' : 'text-amber-600'}`}>{me.eligible ? '✓ ' : '⚠ '}{me.eligibility_reason}</p>
            </div>
            <div className="flex gap-2">
              <button onClick={toggle} disabled={busy === 'avail'}
                      className={`btn ${me.available ? 'bg-emerald-600 text-white hover:bg-emerald-700' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'}`}
                      aria-pressed={me.available}>
                <span className={`w-2.5 h-2.5 rounded-full ${me.available ? 'bg-white' : 'bg-slate-500'}`} />
                {me.available ? 'Available' : 'Unavailable'}
              </button>
              <button className="btn-ghost" onClick={() => setEditing(true)}><Settings className="w-4 h-4" /> Profile</button>
            </div>
          </div>
          {me.latitude == null && <p className="mt-3 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl p-3">Add your approximate location in Profile so we can match you by distance (currently matched by city only).</p>}

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
            <StatCard icon={HeartPulse} label="Availability" value={me.available ? 'Available' : 'Unavailable'} tone={me.available ? 'text-emerald-500' : 'text-slate-400'} />
            <StatCard icon={ShieldCheck} label="Screening" value={me.eligible ? 'Eligible' : 'Not now'} tone={me.eligible ? 'text-sky-500' : 'text-amber-500'} hint="System criteria only" />
            <StatCard icon={Award} label="Total donations" value={me.total_donations} hint={me.last_donation_date ? `Last: ${me.last_donation_date}` : 'No donation recorded'} />
            <StatCard icon={Activity} label="Nearby requests" value={nearby?.requests.length ?? '…'} tone="text-amber-500" />
          </div>
        </>
      )}

      {active.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-black text-navy-900 mb-3">Requests you accepted</h2>
          <div className="space-y-4">
            {active.map((m) => (
              <RequestCard key={m.match_id} req={{ ...m, id: m.request_id, status: m.request_status }} distance={m.distance_km?.toFixed?.(1)}>
                <div className="text-sm text-slate-600 sm:text-right">
                  <p className="flex items-center gap-1 sm:justify-end"><MapPin className="w-4 h-4" />{m.hospital_address}</p>
                  {m.hospital_phone && <a className="flex items-center gap-1 sm:justify-end font-bold text-blood-600" href={`tel:${m.hospital_phone}`}><Phone className="w-4 h-4" />{m.hospital_phone}</a>}
                </div>
                <div className="flex gap-2">
                  {m.latitude != null && <a className="btn-dark btn-sm" target="_blank" rel="noreferrer" href={directionsUrl(m.latitude, m.longitude)}><Navigation className="w-4 h-4" />Directions</a>}
                  <button className="btn-ghost btn-sm" disabled={busy === m.match_id} onClick={() => act(m.match_id, () => api.post(`/matching/${m.match_id}/reject`))}>Withdraw</button>
                </div>
              </RequestCard>
            ))}
          </div>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-black text-navy-900">Matched requests awaiting your response</h2>
        <p className="text-xs text-slate-500 mb-3">Matched based on RBC compatibility, distance, and severity scoring</p>
        {matches === null ? <Skeleton rows={2} /> : pending.length === 0 ? <Empty title="No pending matches right now.">You will get a real-time alert when a compatible request appears nearby.</Empty> : (
          <div className="space-y-4">
            {pending.map((m) => (
              <RequestCard key={m.match_id} req={{ ...m, id: m.request_id, status: m.request_status }} distance={m.distance_km?.toFixed?.(1)}>
                <span className="chip bg-blood-50 text-blood-600 text-sm">Match {m.match_score}%</span>
                <div className="flex gap-2">
                  <button className="btn-primary btn-sm" disabled={busy === m.match_id} onClick={() => act(m.match_id, () => api.post(`/matching/${m.match_id}/accept`))}><Check className="w-4 h-4" />Accept</button>
                  <button className="btn-ghost btn-sm" disabled={busy === m.match_id} onClick={() => act(m.match_id, () => api.post(`/matching/${m.match_id}/reject`))}><X className="w-4 h-4" />Decline</button>
                </div>
              </RequestCard>
            ))}
          </div>
        )}
      </section>

      <section className="mt-8">
        <div className="flex flex-wrap items-end justify-between gap-3 mb-3">
          <div>
            <h2 className="text-lg font-black text-navy-900">Nearby compatible requests</h2>
            <p className="text-xs text-slate-500">Active requests your blood group can serve, most urgent first</p>
          </div>
          <div className="flex gap-2">
            <select className="input py-2 w-auto" value={filters.max_distance_km} onChange={(e) => setFilters({ ...filters, max_distance_km: +e.target.value })} aria-label="Distance">
              {[10, 25, 50, 100, 500].map((d) => <option key={d} value={d}>Within {d} km</option>)}
            </select>
            <select className="input py-2 w-auto" value={filters.emergency_level} onChange={(e) => setFilters({ ...filters, emergency_level: e.target.value })} aria-label="Severity">
              <option value="">All severities</option>{URGENCY.map((u) => <option key={u}>{u}</option>)}
            </select>
          </div>
        </div>
        {nearby === null ? <Skeleton rows={2} /> : nearby.requests.length === 0 ? <Empty title="No nearby emergency requests matching your criteria." /> : (
          <div className="space-y-4">
            {nearby.requests.map((r) => (
              <RequestCard key={r.id} req={r} distance={r.distance_km}>
                {r.match_status === 'ACCEPTED' || r.match_status === 'CONFIRMED'
                  ? <span className="chip bg-emerald-50 text-emerald-700">You accepted</span>
                  : <button className="btn-primary btn-sm" disabled={busy === `r${r.id}` || !nearby.eligible || !nearby.available}
                            title={!nearby.available ? 'Set yourself available first' : !nearby.eligible ? nearby.eligibility_reason : ''}
                            onClick={() => act(`r${r.id}`, () => api.post(`/requests/${r.id}/respond`))}><HeartHandshake className="w-4 h-4" />I can donate</button>}
              </RequestCard>
            ))}
          </div>
        )}
      </section>

      <section className="mt-8 grid lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="font-black text-navy-900">Donation history</h2>
          {donations.length === 0 ? <p className="text-sm text-slate-500 mt-2">No confirmed donations through Blood Bridge yet.</p> : (
            <ul className="mt-3 divide-y divide-slate-100 text-sm">
              {donations.map((d) => (
                <li key={d.id} className="py-2 flex justify-between gap-2"><span>{d.donation_date} · {d.hospital_name || 'Hospital'} · {d.units} unit(s)</span><span className="text-slate-400 text-xs">{d.certificate_number}</span></li>
              ))}
            </ul>
          )}
        </div>
        <div className="card p-6">
          <h2 className="font-black text-navy-900">Past responses</h2>
          {history.length === 0 ? <p className="text-sm text-slate-500 mt-2">Nothing here yet.</p> : (
            <ul className="mt-3 divide-y divide-slate-100 text-sm">
              {history.map((m) => (
                <li key={m.match_id} className="py-2 flex justify-between gap-2"><span>#{m.request_id} · {m.blood_group} · {m.hospital_name}</span><span className="chip bg-slate-100 text-slate-600">{m.match_status}</span></li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <Modal open={editing} title="Donor profile" onClose={() => setEditing(false)}>
        {me && <ProfileEditor me={me} onSaved={load} onClose={() => setEditing(false)} />}
      </Modal>
    </div>
  )
}
