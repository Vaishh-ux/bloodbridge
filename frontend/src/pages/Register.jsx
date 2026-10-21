import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Droplet, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../lib/api'
import { BLOOD_GROUPS, DASHBOARD_PATH, todayISO } from '../lib/blood'
import { ErrorBox, Field } from '../components/ui'
import { LocationPicker } from '../components/MapView'
import { DISCLAIMER } from '../components/Layout'
import { validateRegistration } from '../lib/validation'

const ROLE_TABS = [
  { key: 'DONOR', label: 'Blood Donor' },
  { key: 'PATIENT', label: 'Patient / Seeker' },
  { key: 'HOSPITAL', label: 'Hospital / Blood Bank' },
]

export default function Register() {
  const [params] = useSearchParams()
  const initialRole = ROLE_TABS.some((r) => r.key === params.get('role')) ? params.get('role') : 'DONOR'
  const { register } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({
    role: initialRole, name: '', email: '', phone: '', password: '', confirm: '',
    blood_group: '', date_of_birth: '', gender: '', address: '', city: '', state: '', pincode: '',
    loc: null, last_donation_date: '', available: true, meets_basic_criteria: false, facility_type: 'HOSPITAL',
  })
  const [touched, setTouched] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e?.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e }))
  const errors = useMemo(() => validateRegistration(f), [f])
  const blocking = Object.keys(errors).filter((k) => k !== 'meets_basic_criteria')
  const show = (k) => touched && errors[k] && <span className="block text-xs text-red-600 mt-1">{errors[k]}</span>

  const submit = async (e) => {
    e.preventDefault()
    setTouched(true); setErr('')
    if (blocking.length) return
    setBusy(true)
    const payload = {
      name: f.name.trim(), email: f.email.trim(), phone: f.phone.trim(), password: f.password, role: f.role,
      blood_group: f.blood_group || null, date_of_birth: f.date_of_birth || null, gender: f.gender || null,
      address: f.address.trim() || null, city: f.city.trim(), state: f.state.trim(), pincode: f.pincode.trim() || null,
      latitude: f.loc?.lat ?? null, longitude: f.loc?.lng ?? null,
    }
    if (f.role === 'DONOR') Object.assign(payload, {
      available: f.available, last_donation_date: f.last_donation_date || null, meets_basic_criteria: f.meets_basic_criteria,
    })
    if (f.role === 'HOSPITAL') payload.facility_type = f.facility_type
    try {
      const me = await register(payload)
      nav(DASHBOARD_PATH[me.role], { replace: true })
    } catch (e2) {
      setErr(errorMessage(e2, 'Registration failed. Please try again.'))
    } finally { setBusy(false) }
  }

  const isDonor = f.role === 'DONOR'
  const isHospital = f.role === 'HOSPITAL'

  return (
    <div className="bg-slate-50 py-12 px-4">
      <form onSubmit={submit} className="card max-w-2xl mx-auto p-6 sm:p-10 shadow-xl" noValidate>
        <div className="w-14 h-14 rounded-2xl bg-blood-600 mx-auto flex items-center justify-center shadow-lg shadow-blood-600/30">
          <Droplet className="w-6 h-6 text-white fill-white" />
        </div>
        <h1 className="text-2xl font-black text-center text-navy-900 mt-4">Create Blood Bridge Account</h1>
        <p className="text-xs text-center text-slate-500 mt-1">Join the real-time blood request and donor network</p>

        <p className="label mt-8">Register as</p>
        <div className="grid grid-cols-3 gap-2" role="radiogroup">
          {ROLE_TABS.map((r) => (
            <button type="button" key={r.key} role="radio" aria-checked={f.role === r.key} onClick={() => set('role')(r.key)}
                    className={`rounded-2xl py-3 text-xs font-bold border transition ${f.role === r.key ? 'bg-blood-600 text-white border-blood-600 shadow-lg shadow-blood-600/25' : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'}`}>
              {r.label}
            </button>
          ))}
        </div>

        <div className="grid sm:grid-cols-2 gap-5 mt-6">
          <Field label={isHospital ? 'Hospital / blood bank name' : 'Full name'} required>
            <input className="input" value={f.name} onChange={set('name')} placeholder={isHospital ? 'City Care Hospital' : 'Your full name'} autoComplete="name" />{show('name')}
          </Field>
          <Field label="Email address" required>
            <input className="input" type="email" value={f.email} onChange={set('email')} placeholder="name@example.com" autoComplete="email" />{show('email')}
          </Field>
          <Field label="Phone number" required>
            <input className="input" type="tel" value={f.phone} onChange={set('phone')} placeholder="+91 98765 43210" autoComplete="tel" />{show('phone')}
          </Field>
          {isHospital && (
            <Field label="Facility type" required>
              <select className="input" value={f.facility_type} onChange={set('facility_type')}>
                <option value="HOSPITAL">Hospital</option><option value="BLOOD_BANK">Blood bank</option>
              </select>
            </Field>
          )}
          <Field label="Password" required hint="Min. 8 characters, with a letter and a number.">
            <input className="input" type="password" value={f.password} onChange={set('password')} autoComplete="new-password" />{show('password')}
          </Field>
          <Field label="Confirm password" required>
            <input className="input" type="password" value={f.confirm} onChange={set('confirm')} autoComplete="new-password" />{show('confirm')}
          </Field>
        </div>

        {!isHospital && (
          <div className="grid sm:grid-cols-3 gap-4 mt-6 rounded-2xl bg-blood-50/40 border border-blood-100 p-4">
            <Field label="Blood group" required={isDonor}>
              <select className="input bg-white font-bold text-blood-600" value={f.blood_group} onChange={set('blood_group')}>
                <option value="">{isDonor ? 'Select' : 'Not sure'}</option>
                {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
              </select>{show('blood_group')}
            </Field>
            <Field label="Date of birth">
              <input className="input bg-white" type="date" max={todayISO()} value={f.date_of_birth} onChange={set('date_of_birth')} />
            </Field>
            <Field label="Gender">
              <select className="input bg-white" value={f.gender} onChange={set('gender')}>
                <option value="">Prefer not to say</option><option>Male</option><option>Female</option><option>Other</option>
              </select>
            </Field>
          </div>
        )}

        <div className="grid sm:grid-cols-3 gap-4 mt-6">
          <div className="sm:col-span-3">
            <Field label={isHospital ? 'Facility address' : 'Address / area'} required={isHospital}>
              <input className="input" value={f.address} onChange={set('address')} placeholder="Street, area" autoComplete="street-address" />{show('address')}
            </Field>
          </div>
          <Field label="City" required><input className="input" value={f.city} onChange={set('city')} autoComplete="address-level2" />{show('city')}</Field>
          <Field label="State" required><input className="input" value={f.state} onChange={set('state')} autoComplete="address-level1" />{show('state')}</Field>
          <Field label="PIN code"><input className="input" value={f.pincode} onChange={set('pincode')} inputMode="numeric" autoComplete="postal-code" /></Field>
        </div>

        {(isDonor || isHospital) && (
          <div className="mt-6">
            <LocationPicker value={f.loc} onChange={set('loc')}
                            label={isHospital ? 'Facility location (required)' : 'Your approximate location (recommended)'}
                            addressHint={[f.address, f.city, f.pincode, f.state].filter(Boolean).join(', ')} />
            {show('loc')}
            {isDonor && <p className="text-xs text-slate-500 mt-2">Used only to compute distance to requests. Your exact location and contact details are never shown publicly; without a location you are matched by city.</p>}
          </div>
        )}

        {isDonor && (
          <div className="mt-6 rounded-2xl bg-slate-50 border border-slate-100 p-5">
            <p className="font-black text-sm text-navy-900 uppercase tracking-wide">Donor screening details</p>
            <div className="grid sm:grid-cols-2 gap-4 mt-3 items-end">
              <Field label="Last blood donation date" hint="Leave empty if you have never donated.">
                <input className="input bg-white" type="date" max={todayISO()} value={f.last_donation_date} onChange={set('last_donation_date')} />
              </Field>
              <label className="flex items-center gap-2 text-sm font-bold text-slate-700 pb-3">
                <input type="checkbox" className="w-4 h-4 accent-blood-600" checked={f.available} onChange={set('available')} />
                Currently available for emergency calls
              </label>
            </div>
            <label className="flex gap-3 mt-4 text-sm text-slate-700">
              <input type="checkbox" className="w-4 h-4 mt-0.5 accent-blood-600" checked={f.meets_basic_criteria} onChange={set('meets_basic_criteria')} />
              <span>I am 18–65 years old, weigh at least 45 kg, feel healthy today, and am not aware of any condition, recent
                illness, tattoo/piercing or medication that would prevent me from donating. <Link to="/donate" className="text-blood-600 font-bold" target="_blank">Read the guide</Link></span>
            </label>
            {touched && errors.meets_basic_criteria && <p className="text-xs text-amber-700 mt-2">{errors.meets_basic_criteria}</p>}
            <p className="text-[11px] text-slate-500 mt-3">{DISCLAIMER}</p>
          </div>
        )}

        <div className="mt-6"><ErrorBox message={err} /></div>
        {touched && blocking.length > 0 && <p className="mt-4 text-sm text-red-600">Please fix the highlighted fields.</p>}
        <button className="btn-primary w-full mt-6 py-4 text-base" disabled={busy}>
          {busy && <Loader2 className="w-4 h-4 animate-spin" />} Complete Registration
        </button>
        <p className="text-center text-xs text-slate-500 mt-6 pt-6 border-t border-slate-100">
          Already have an account? <Link to="/login" className="font-bold text-blood-600">Sign in</Link>
        </p>
      </form>
    </div>
  )
}
