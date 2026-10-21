import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Crosshair, Search, ShieldCheck, Users } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, canReceiveFrom } from '../lib/blood'
import { currentPosition } from '../lib/geo'
import { BloodBadge, Empty, ErrorBox, Field, PageHeader, Skeleton } from '../components/ui'

export default function FindDonors() {
  const [f, setF] = useState({ compatible_with: '', city: '', pincode: '', available_only: true, eligible_only: true, radius_km: 25 })
  const [me, setMe] = useState(null)
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const search = async (e) => {
    e?.preventDefault()
    setBusy(true); setErr('')
    try {
      const params = { available_only: f.available_only, eligible_only: f.eligible_only }
      if (f.compatible_with) params.compatible_with = f.compatible_with
      if (f.city.trim()) params.city = f.city.trim()
      if (f.pincode.trim()) params.pincode = f.pincode.trim()
      if (me) Object.assign(params, { lat: me.lat, lng: me.lng, radius_km: f.radius_km })
      const { data } = await api.get('/donors', { params })
      setRes(data)
    } catch (e2) { setErr(errorMessage(e2)) } finally { setBusy(false) }
  }
  const locate = async () => {
    try { setMe(await currentPosition()) } catch (e) { setErr(e.message) }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <PageHeader icon={Users} title="Find Compatible Donors"
                  subtitle="Search registered donors by blood group, city, PIN code and distance. Personal details stay private." />
      <form onSubmit={search} className="card p-6 grid sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
        <Field label="Patient blood group">
          <select className="input font-bold text-blood-600" value={f.compatible_with} onChange={set('compatible_with')}>
            <option value="">Any</option>{BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
          </select>
        </Field>
        <Field label="City / area"><input className="input" value={f.city} onChange={set('city')} placeholder="e.g. Chennai" /></Field>
        <Field label="PIN code"><input className="input" value={f.pincode} onChange={set('pincode')} inputMode="numeric" /></Field>
        {me ? (
          <Field label={`Within ${f.radius_km} km of you`}>
            <input type="range" min={2} max={100} value={f.radius_km} onChange={set('radius_km')} className="w-full accent-blood-600" />
          </Field>
        ) : (
          <div>
            <span className="label">Distance</span>
            <button type="button" onClick={locate} className="btn-ghost w-full"><Crosshair className="w-4 h-4" /> Use my location</button>
          </div>
        )}
        <label className="flex items-center gap-2 text-sm font-bold text-slate-700"><input type="checkbox" className="accent-blood-600" checked={f.available_only} onChange={set('available_only')} /> Available now</label>
        <label className="flex items-center gap-2 text-sm font-bold text-slate-700"><input type="checkbox" className="accent-blood-600" checked={f.eligible_only} onChange={set('eligible_only')} /> Passes screening criteria</label>
        <div className="lg:col-span-2 flex justify-end"><button className="btn-primary" disabled={busy}><Search className="w-4 h-4" /> Search donors</button></div>
      </form>
      {f.compatible_with && <p className="text-xs text-slate-500 mt-3">A {f.compatible_with} patient can receive red cells from: <strong>{canReceiveFrom(f.compatible_with).join(', ')}</strong></p>}

      <div className="mt-6 rounded-2xl bg-sky-50 border border-sky-100 p-4 text-sm text-sky-800 flex gap-3">
        <ShieldCheck className="w-5 h-5 shrink-0" />
        <span>To protect donors, phone numbers, addresses and exact locations are never listed. To reach these donors,
          <Link to="/create-request" className="font-bold underline mx-1">create a blood request</Link>— compatible donors are alerted and can choose to accept and share contact details.</span>
      </div>

      <div className="mt-6"><ErrorBox message={err} /></div>
      {busy && <Skeleton rows={3} />}
      {!busy && res && (res.count === 0
        ? <Empty title="No matching donors found">Try a wider area, another city, or create a request so new donors are matched automatically.</Empty>
        : (
          <>
            <p className="text-sm font-bold text-slate-600 mb-3">{res.count} donor{res.count > 1 ? 's' : ''} found</p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {res.donors.map((d) => (
                <div key={d.donor_ref} className="card p-5 flex gap-4">
                  <BloodBadge group={d.blood_group} />
                  <div className="min-w-0">
                    <p className="font-black text-navy-900">{d.display_name}</p>
                    <p className="text-sm text-slate-500">{d.city}{d.area_pincode ? ` · ${d.area_pincode}` : ''}{d.distance_km != null ? ` · ${d.distance_km} km` : ''}</p>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      <span className={`chip ${d.available ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{d.available ? 'Available' : 'Unavailable'}</span>
                      <span className={`chip ${d.eligible ? 'bg-sky-50 text-sky-700' : 'bg-amber-50 text-amber-700'}`} title={d.eligibility_note}>{d.eligible ? 'Eligible for screening' : 'Not eligible now'}</span>
                    </div>
                    {d.successful_donations > 0 && <p className="text-xs text-slate-500 mt-2">{d.successful_donations} confirmed donation(s) via Blood Bridge</p>}
                  </div>
                </div>
              ))}
            </div>
          </>
        ))}
    </div>
  )
}
