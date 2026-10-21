import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Droplet, Loader2, Siren, UserPlus } from 'lucide-react'
import api, { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, URGENCY, canReceiveFrom, todayISO } from '../lib/blood'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { ErrorBox, Field, PageHeader, Spinner } from '../components/ui'
import { LocationPicker } from '../components/MapView'

const REQUESTER_ROLES = ['PATIENT', 'HOSPITAL', 'ADMIN']

/** Visitors can submit in one step: a patient account is created from these details first. */
function guestErrors(g) {
  if (g.name.trim().length < 2) return 'Enter your name in "Your contact details".'
  if (!/^\+?[0-9][0-9\s-]{6,18}$/.test(g.phone.trim())) return 'Enter a valid phone number so the hospital and donors can reach you.'
  if (!/^\S+@\S+\.\S+$/.test(g.email.trim())) return 'Enter a valid email address.'
  if (g.password.length < 8 || !/[A-Za-z]/.test(g.password) || !/\d/.test(g.password)) return 'Choose a password with at least 8 characters, including a letter and a number.'
  return ''
}

export default function CreateRequest() {
  const { user, loading, register } = useAuth()
  if (loading) return <Spinner />
  if (user && !REQUESTER_ROLES.includes(user.role)) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16">
        <div className="card p-8 text-center">
          <p className="font-black text-xl text-navy-900">Donor accounts can’t create blood requests</p>
          <p className="text-sm text-slate-500 mt-2">Log out and request as a visitor or patient, or ask the hospital to raise the request.</p>
          <Link to="/emergency" className="btn-primary mt-6">Emergency help</Link>
        </div>
      </div>
    )
  }
  return <RequestForm user={user} register={register} />
}

function RequestForm({ user, register }) {
  const toast = useToast()
  const nav = useNavigate()
  const isGuest = !user
  const isHospital = user?.role === 'HOSPITAL'
  const [guest, setGuest] = useState({ name: '', phone: '', email: '', password: '' })
  const setG = (k) => (e) => setGuest((s) => ({ ...s, [k]: e.target.value }))
  const [facilities, setFacilities] = useState([])
  const soon = new Date(Date.now() + 2 * 3600 * 1000)
  const soonDate = new Date(soon.getTime() - soon.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
  const [f, setF] = useState({
    patient_name: '', blood_group: '', units_required: 1, emergency_level: 'High', hospital_id: '',
    hospital_name: '', hospital_address: '', city: '', state: '', loc: null,
    required_date: soonDate, required_time: `${String(soon.getHours()).padStart(2, '0')}:00`, notes: '',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e?.target ? e.target.value : e }))

  useEffect(() => { if (!isHospital) api.get('/hospitals').then((r) => setFacilities(r.data)).catch(() => {}) }, [isHospital])
  const picked = facilities.find((h) => String(h.id) === String(f.hospital_id))
  const manual = !isHospital && !picked

  const validate = () => {
    if (isGuest) { const g = guestErrors(guest); if (g) return g }
    if (!f.blood_group) return 'Select the blood group required.'
    if (!(+f.units_required >= 1 && +f.units_required <= 20)) return 'Units must be between 1 and 20.'
    if (!f.emergency_level) return 'Select an emergency level.'
    if (!f.required_date || f.required_date < todayISO()) return 'Required date cannot be in the past.'
    if (manual) {
      if (!f.hospital_name.trim() || !f.hospital_address.trim() || !f.city.trim() || !f.state.trim()) return 'Hospital name, address, city and state are required.'
      if (!f.loc) return 'Set the hospital location (Locate / Use my location / click the map) so nearby donors can be matched.'
    }
    return ''
  }

  const submit = async (e) => {
    e.preventDefault()
    const v = validate()
    setErr(v)
    if (v) return
    setBusy(true)
    const body = {
      patient_name: f.patient_name.trim() || null, blood_group: f.blood_group, units_required: +f.units_required,
      emergency_level: f.emergency_level, required_date: f.required_date, required_time: f.required_time,
      notes: f.notes.trim() || null,
    }
    if (picked) body.hospital_id = picked.id
    else if (manual) Object.assign(body, {
      hospital_name: f.hospital_name.trim(), hospital_address: f.hospital_address.trim(), city: f.city.trim(),
      state: f.state.trim(), latitude: f.loc.lat, longitude: f.loc.lng,
    })
    let role = user?.role
    if (isGuest) {
      try {
        const me = await register({
          role: 'PATIENT', name: guest.name.trim(), phone: guest.phone.trim(), email: guest.email.trim(),
          password: guest.password, city: (picked?.city || f.city).trim(), state: (picked?.state || f.state).trim(),
        })
        role = me?.role || 'PATIENT'
      } catch (e2) {
        setErr(errorMessage(e2, 'Could not create your account.'))
        setBusy(false)
        return
      }
    }
    try {
      const { data } = await api.post('/requests', body)
      toast.success(data.message, `Request #${data.id} created`)
      nav(role === 'HOSPITAL' ? '/hospital-dashboard' : role === 'ADMIN' ? '/admin-dashboard' : '/patient-dashboard')
    } catch (e2) {
      setErr(errorMessage(e2, 'Could not create the request.') + (isGuest ? ' Your account was created, so you are now logged in — fix the issue and submit again.' : ''))
    } finally { setBusy(false) }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <PageHeader icon={Droplet} title="Create Emergency Blood Request" subtitle="Compatible, available donors nearby are matched and alerted the moment you submit." />
      <div className="mb-6 rounded-2xl bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800 flex gap-3">
        <Siren className="w-5 h-5 shrink-0" />
        <span>In a life-threatening emergency, call <strong>112</strong> or <strong>108</strong> and contact the hospital blood bank directly. Blood Bridge supplements, never replaces, hospital procedures. <Link to="/emergency" className="font-bold underline">Emergency help</Link></span>
      </div>
      <form onSubmit={submit} className="card p-6 sm:p-8 space-y-6" noValidate>
        {isGuest && (
          <div className="rounded-2xl border border-blood-100 bg-blood-50/40 p-5">
            <p className="font-black text-navy-900 flex items-center gap-2"><UserPlus className="w-5 h-5 text-blood-600" />Your contact details</p>
            <p className="text-xs text-slate-600 mt-1">
              No separate sign-up needed: we create your requester account and submit the request in one step, so you can
              track it and see donors who accept. Already registered? <Link to="/login" state={{ from: '/create-request' }} className="font-bold text-blood-600">Log in</Link>
            </p>
            <div className="grid sm:grid-cols-2 gap-4 mt-4">
              <Field label="Your name" required><input className="input bg-white" autoComplete="name" value={guest.name} onChange={setG('name')} /></Field>
              <Field label="Phone number" required><input className="input bg-white" type="tel" autoComplete="tel" placeholder="+91 98765 43210" value={guest.phone} onChange={setG('phone')} /></Field>
              <Field label="Email" required><input className="input bg-white" type="email" autoComplete="email" value={guest.email} onChange={setG('email')} /></Field>
              <Field label="Create a password" required hint="Min. 8 characters with a letter and a number — to track this request later.">
                <input className="input bg-white" type="password" autoComplete="new-password" value={guest.password} onChange={setG('password')} />
              </Field>
            </div>
          </div>
        )}
        <div className="grid sm:grid-cols-3 gap-4">
          <Field label="Blood group required" required>
            <select className="input font-bold text-blood-600" value={f.blood_group} onChange={set('blood_group')}>
              <option value="">Select</option>{BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
            </select>
          </Field>
          <Field label="Units required" required>
            <input className="input" type="number" min={1} max={20} value={f.units_required} onChange={set('units_required')} />
          </Field>
          <Field label="Emergency level" required>
            <select className="input" value={f.emergency_level} onChange={set('emergency_level')}>{URGENCY.map((u) => <option key={u}>{u}</option>)}</select>
          </Field>
        </div>
        {f.blood_group && <p className="text-xs text-slate-500 -mt-3">Compatible donor groups (red cells): <strong>{canReceiveFrom(f.blood_group).join(', ')}</strong></p>}

        <Field label="Patient name (private)" hint="Visible only to you, the hospital and administrators — never on the public feed.">
          <input className="input" value={f.patient_name} onChange={set('patient_name')} />
        </Field>

        {!isHospital && (
          <Field label="Hospital" hint="Pick a registered facility, or choose 'Other' and enter the details.">
            <select className="input" value={f.hospital_id} onChange={set('hospital_id')}>
              <option value="">Other / not listed</option>
              {facilities.map((h) => <option key={h.id} value={h.id}>{h.name} — {h.city}{h.verified ? ' ✓' : ''}</option>)}
            </select>
          </Field>
        )}
        {isHospital && <p className="text-sm text-slate-600">Request will be created for <strong>{user?.profile?.name}</strong> at your registered location.</p>}

        {manual && (
          <>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Hospital name" required><input className="input" value={f.hospital_name} onChange={set('hospital_name')} /></Field>
              <Field label="Hospital address" required><input className="input" value={f.hospital_address} onChange={set('hospital_address')} /></Field>
              <Field label="City" required><input className="input" value={f.city} onChange={set('city')} /></Field>
              <Field label="State" required><input className="input" value={f.state} onChange={set('state')} /></Field>
            </div>
            <LocationPicker label="Hospital location (required)" value={f.loc} onChange={set('loc')}
                            addressHint={[f.hospital_name, f.hospital_address, f.city, f.state].filter(Boolean).join(', ')} />
          </>
        )}

        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Required date" required><input className="input" type="date" min={todayISO()} value={f.required_date} onChange={set('required_date')} /></Field>
          <Field label="Required time" required><input className="input" type="time" value={f.required_time} onChange={set('required_time')} /></Field>
        </div>
        <Field label="Additional notes (private)" hint="E.g. ward/contact desk. Shown only to the hospital and administrators.">
          <textarea className="input min-h-[90px]" maxLength={1000} value={f.notes} onChange={set('notes')} />
        </Field>

        <ErrorBox message={err} />
        <button className="btn-primary w-full py-4 text-base" disabled={busy}>
          {busy && <Loader2 className="w-4 h-4 animate-spin" />} Submit Request &amp; Find Donors
        </button>
      </form>
    </div>
  )
}
